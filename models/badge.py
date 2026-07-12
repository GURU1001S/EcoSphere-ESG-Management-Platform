# -*- coding: utf-8 -*-
from odoo import models, fields, api

class EcoBadgeFamily(models.Model):
    _name = 'eco.badge.family'
    _description = 'Badge Family Progression'
    _order = 'sequence, id'

    name = fields.Char(string='Family Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    badge_ids = fields.One2many('eco.badge', 'badge_family_id', string='Badges')

class EcoBadge(models.Model):
    _name = 'eco.badge'
    _description = 'EcoSphere Badge'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Text(string='Description')
    icon = fields.Binary(string='Icon')
    
    unlock_rule = fields.Selection([
        ('xp_threshold', 'XP Threshold'),
        ('challenge_count', 'Challenge Count'),
        ('streak', 'Consecutive Weeks Active'),
        ('category_specialist', 'Category Specialist'),
        ('impact_score_avg', 'Impact Score Average'),
        ('early_adopter', 'Early Adopter'),
        ('department_champion', 'Department Champion')
    ], string='Unlock Rule', required=True, tracking=True)
    
    unlock_value = fields.Integer(string='Unlock Value', default=0, tracking=True)
    
    employee_ids = fields.Many2many('hr.employee', string='Awarded Employees')
    
    rarity = fields.Selection([
        ('common', 'Common'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary')
    ], string='Rarity', default='common', tracking=True)
    
    badge_family_id = fields.Many2one('eco.badge.family', string='Badge Family')
    
    auto_expiry = fields.Boolean(string='Auto Expiry', default=False, tracking=True)
    expiry_days = fields.Integer(string='Expiry Days', default=0)

    def check_unlock(self, employee):
        """
        Evaluates the unlock_rule against an employee record.
        Returns True if the criteria is met, False otherwise.
        Called from challenge_participation.py on approval.
        """
        self.ensure_one()
        
        if self.unlock_rule == 'xp_threshold':
            return employee.xp >= self.unlock_value
            
        elif self.unlock_rule == 'challenge_count':
            return employee.completed_challenge_count >= self.unlock_value
            
        elif self.unlock_rule == 'streak':
            # TODO: Implement streak logic (N consecutive weeks active)
            return False
            
        elif self.unlock_rule == 'category_specialist':
            approved_parts = employee.challenge_participation_ids.filtered(lambda p: p.approval_status == 'approved')
            category_counts = {}
            for part in approved_parts:
                cat_id = part.challenge_id.category_id.id
                if cat_id:
                    category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
                    if category_counts[cat_id] >= self.unlock_value:
                        return True
            return False
            
        elif self.unlock_rule == 'impact_score_avg':
            # TODO: Implement AI impact score logic
            return False
            
        elif self.unlock_rule == 'early_adopter':
            # TODO: "first 10" tracking logic. Wire it in Stage 4 if time allows.
            return False
            
        elif self.unlock_rule == 'department_champion':
            if not employee.department_id:
                return False
            dept_employees = self.env['hr.employee'].search([('department_id', '=', employee.department_id.id)])
            max_xp = max(dept_employees.mapped('xp') or [0])
            return employee.xp >= max_xp and employee.xp > 0
            
        return False
