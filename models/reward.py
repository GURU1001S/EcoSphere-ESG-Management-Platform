# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class EcoReward(models.Model):
    _name = 'esg.reward'
    _description = 'EcoSphere Reward'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Text(string='Description')
    points_required = fields.Integer(string='Points Required', default=0, tracking=True)
    stock = fields.Integer(string='Stock', default=0, tracking=True)
    status = fields.Selection([
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock')
    ], string='Status', default='available', tracking=True)
    
    reward_category = fields.Selection([
        ('wellness', 'Wellness'),
        ('learning', 'Learning'),
        ('recognition', 'Recognition'),
        ('experience', 'Experience'),
        ('sustainability_product', 'Sustainability Product')
    ], string='Reward Category', tracking=True)
    
    target_sentiment = fields.Selection([
        ('all', 'All'),
        ('struggling', 'Struggling'),
        ('high_performer', 'High Performer')
    ], string='Target Sentiment', default='all', tracking=True)
    
    discount_for_streak = fields.Boolean(string='Discount for Streak', default=False, tracking=True)
    
    popularity_score = fields.Float(
        string='Popularity Score', 
        compute='_compute_popularity_score', 
        store=True,
        tracking=True
    )
    
    redemption_ids = fields.One2many('esg.reward.redemption', 'reward_id', string='Redemptions')

    @api.depends('redemption_ids')
    def _compute_popularity_score(self):
        total_employees = self.env['hr.employee'].search_count([('active', '=', True)])
        if total_employees == 0:
            total_employees = 1 # Prevent division by zero
            
        for reward in self:
            redemption_count = len(reward.redemption_ids)
            reward.popularity_score = redemption_count / total_employees

    def action_redeem(self, employee_id=None):
        self.ensure_one()

        employee = self.env['hr.employee'].browse(employee_id) if employee_id else self.env.user.employee_id
        if not employee.exists():
            raise UserError("Employee not found.")
        if not self._is_available_for_employee(employee):
            raise UserError("This reward is not currently available for this employee's engagement profile.")
            
        if self.status == 'out_of_stock' or self.stock <= 0:
            raise UserError("This reward is currently out of stock.")
            
        points_cost = self.points_required
        
        # Apply 20% discount if eligible
        if self.discount_for_streak:
            # We reference employee.streak even if it doesn't exist yet, per instruction.
            # Wrapped in a try/except so you don't get 500 errors if you test it before Stage 3.
            try:
                if employee.streak >= 3:
                    points_cost = int(points_cost * 0.8)
            except AttributeError:
                pass
                
        if getattr(employee, 'points', 0) < points_cost:
            raise UserError(f"Employee does not have enough points. (Required: {points_cost}, Available: {getattr(employee, 'points', 0)})")
            
        # Perform redemption
        employee.points -= points_cost
        self.stock -= 1
        
        if self.stock <= 0:
            self.status = 'out_of_stock'
            
        # Create redemption record
        self.env['esg.reward.redemption'].create({
            'employee_id': employee.id,
            'reward_id': self.id,
            'points_spent': points_cost,
        })
        
        self.message_post(body=f"Reward redeemed by {employee.name} for {points_cost} points.")
        return True

    def _is_available_for_employee(self, employee):
        self.ensure_one()
        if self.target_sentiment == 'all':
            return True
        if self.target_sentiment == 'struggling':
            return employee.sentiment_tag in ('inactive', 'struggling')
        if self.target_sentiment == 'high_performer':
            return employee.sentiment_tag in ('motivated', 'champion')
        return True

    @api.model
    def get_available_rewards_for_employee(self, employee):
        rewards = self.search([('status', '=', 'available'), ('stock', '>', 0)])
        return rewards.filtered(lambda reward: reward._is_available_for_employee(employee))
