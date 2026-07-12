# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class EcoEmployeeParticipation(models.Model):
    _name = 'esg.employee.participation'
    _description = 'CSR Activity Participation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    activity_id = fields.Many2one('esg.csr.activity', string='CSR Activity', required=True, tracking=True)
    
    proof = fields.Binary(string='Proof File')
    proof_filename = fields.Char(string='Proof Filename')
    
    approval_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='pending', tracking=True)
    
    points_earned = fields.Integer(string='Points Earned', default=0, tracking=True)
    completion_date = fields.Date(string='Completion Date', default=fields.Date.context_today)
    notes = fields.Text(string='Notes')
    
    impact_category = fields.Selection([
        ('environmental', 'Environmental'),
        ('social', 'Social'),
        ('community', 'Community'),
        ('health', 'Health & Wellbeing')
    ], string='Impact Category', tracking=True)
    
    self_reported_impact = fields.Text(string='Self-Reported Impact')
    ai_impact_score = fields.Integer(string='AI Impact Score (1-10)', default=5, tracking=True)
    verified_hours = fields.Float(string='Verified Hours')
    
    points_multiplier = fields.Float(string='Points Multiplier', compute='_compute_multiplier', store=True)

    @api.depends('ai_impact_score')
    def _compute_multiplier(self):
        for rec in self:
            rec.points_multiplier = rec.ai_impact_score / 10.0

    def action_approve(self):
        for rec in self:
            rec.approval_status = 'approved'
        return True
        
    def action_reject(self):
        for rec in self:
            rec.approval_status = 'rejected'
        return True

    def write(self, vals):
        status_changed = 'approval_status' in vals
        old_statuses = {rec.id: rec.approval_status for rec in self} if status_changed else {}
        
        res = super(EcoEmployeeParticipation, self).write(vals)
        
        if status_changed:
            for rec in self:
                if rec.approval_status == 'approved' and old_statuses.get(rec.id) != 'approved':
                    rec._handle_approval()
                elif rec.approval_status == 'rejected' and old_statuses.get(rec.id) != 'rejected':
                    rec._handle_rejection()
        return res

    def _handle_approval(self):
        self.ensure_one()
        
        # 1. Config Toggle Check
        config = self.env['ir.config_parameter'].sudo()
        evidence_required = config.get_param('ecosphere.evidence_required', False)
        
        if evidence_required and not self.proof:
            raise ValidationError("Evidence (proof) is strictly required for approval per company settings. Please upload a file before approving.")
            
        # 2. AI Scoring
        if self.self_reported_impact:
            self._score_impact_with_ai()
        else:
            self.ai_impact_score = 5
            
        # 3. Points Calculation
        base_points = getattr(self.activity_id, 'points_reward', 0)
        multiplier = self.ai_impact_score / 10.0
        
        # Force write multiplier immediately so it's consistent
        self.points_multiplier = multiplier
        self.points_earned = int(base_points * multiplier)
        
        # 4. Award to Employee
        if self.employee_id:
            self.employee_id.points += self.points_earned
            self.employee_id.message_post(body=f"🎉 You earned {self.points_earned} points for participating in {self.activity_id.name}!")
            
    def _handle_rejection(self):
        self.ensure_one()
        partner_ids = [self.employee_id.user_id.partner_id.id] if self.employee_id and self.employee_id.user_id else []
        self.message_post(
            body=f"Your CSR participation in '{self.activity_id.name}' was rejected. Please review the activity requirements.",
            partner_ids=partner_ids
        )

    def _score_impact_with_ai(self):
        """Scores the self-reported impact heuristically based on length/effort."""
        if not self.self_reported_impact:
            self.ai_impact_score = 5
            return

