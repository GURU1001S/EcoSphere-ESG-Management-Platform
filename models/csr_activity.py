# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class EcoCSRActivity(models.Model):
    _name = 'esg.csr.activity'
    _description = 'CSR Activity'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title', required=True, tracking=True)
    description = fields.Text(string='Description')
    department_id = fields.Many2one('esg.department', string='Sponsoring Department')
    
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    points_reward = fields.Integer(string='Base Points Reward', default=0)
    
    participation_ids = fields.One2many('esg.employee.participation', 'activity_id', string='Participations')
    
    target_sdg = fields.Selection([
        ('sdg1', 'SDG 1 - No Poverty'),
        ('sdg2', 'SDG 2 - Zero Hunger'),
        ('sdg3', 'SDG 3 - Good Health and Well-being'),
        ('sdg4', 'SDG 4 - Quality Education'),
        ('sdg5', 'SDG 5 - Gender Equality'),
        ('sdg6', 'SDG 6 - Clean Water and Sanitation'),
        ('sdg7', 'SDG 7 - Affordable and Clean Energy'),
        ('sdg8', 'SDG 8 - Decent Work and Economic Growth'),
        ('sdg9', 'SDG 9 - Industry, Innovation and Infrastructure'),
        ('sdg10', 'SDG 10 - Reduced Inequality'),
        ('sdg11', 'SDG 11 - Sustainable Cities and Communities'),
        ('sdg12', 'SDG 12 - Responsible Consumption and Production'),
        ('sdg13', 'SDG 13 - Climate Action'),
        ('sdg14', 'SDG 14 - Life Below Water'),
        ('sdg15', 'SDG 15 - Life on Land'),
        ('sdg16', 'SDG 16 - Peace and Justice Strong Institutions'),
        ('sdg17', 'SDG 17 - Partnerships to achieve the Goal')
    ], string='Target SDG')
    
    expected_impact = fields.Text(string='Expected Impact')
    
    # R&D Intelligence Fields
    participant_count = fields.Integer(string='Participant Count', compute='_compute_participants')
    actual_impact_score = fields.Float(string='Actual Impact Score', compute='_compute_actual_impact_score', store=True)
    participation_rate = fields.Float(string='Participation Rate', compute='_compute_participation_rate')
    
    ai_summary = fields.Text(string='AI Impact Summary')
    carbon_offset_kg = fields.Float(string='Carbon Offset (kg)')
    
    @api.depends('participation_ids')
    def _compute_participants(self):
        for rec in self:
            rec.participant_count = len(rec.participation_ids)
            
    @api.depends('participation_ids.ai_impact_score')
    def _compute_actual_impact_score(self):
        for rec in self:
            if rec.participation_ids:
                scores = rec.participation_ids.mapped('ai_impact_score')
                rec.actual_impact_score = sum(scores) / len(scores) if scores else 0.0
            else:
                rec.actual_impact_score = 0.0
                
    @api.depends('participant_count', 'department_id')
    def _compute_participation_rate(self):
        """
        Dynamically computes participation rate based on actual employees in the department.
        """
        for rec in self:
            if rec.department_id:
                # Count employees in this ESG department
                emp_count = self.env['hr.employee'].search_count([('esg_department_id', '=', rec.department_id.id)])
                if emp_count > 0:
                    rec.participation_rate = rec.participant_count / emp_count
                else:
                    rec.participation_rate = 0.0
            else:
                rec.participation_rate = 0.0
                
    # State transition buttons
    def action_activate(self):
        for rec in self:
            rec.state = 'active'
            
    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            
    def action_complete(self):
        """Marks activity as complete and immediately fires the AI Impact summary generator."""
        for rec in self:
            rec.state = 'completed'
            rec._generate_ai_summary()
            
    def _generate_ai_summary(self):
        """Generates a local summary of participant self-reported impacts."""
        participations = self.participation_ids.filtered(lambda p: p.approval_status == 'approved' and p.self_reported_impact)
        impact_texts = participations.mapped('self_reported_impact')
        
        if not impact_texts:
            self.message_post(body="✅ Activity marked as completed. *(Summary skipped: No self-reported impact data was provided by participants)*")
            return
            
        # Take up to 5 most recent impacts
        recent_texts = impact_texts[:5]
        combined_text = "<br/>".join(f"- {text}" for text in recent_texts)
        
        res_text = "Overall Impact Highlights:<br/>" + combined_text
        self.ai_summary = res_text
        self.message_post(body=f"<b>Impact Summary:</b><br/>{res_text}")
