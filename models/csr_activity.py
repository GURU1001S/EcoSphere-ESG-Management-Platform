# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class EcoCSRActivity(models.Model):
    _name = 'eco.csr.activity'
    _description = 'CSR Activity'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title', required=True, tracking=True)
    description = fields.Text(string='Description')
    department_id = fields.Many2one('eco.department', string='Sponsoring Department')
    
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    points_reward = fields.Integer(string='Base Points Reward', default=0)
    
    participation_ids = fields.One2many('eco.employee.participation', 'activity_id', string='Participations')
    
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
        Safely computes participation rate. 
        Uses try/except to guard against department_id not having employee_count
        if Person A hasn't built that field on eco.department yet!
        """
        for rec in self:
            try:
                if rec.department_id and hasattr(rec.department_id, 'employee_count') and rec.department_id.employee_count > 0:
                    rec.participation_rate = rec.participant_count / rec.department_id.employee_count
                else:
                    rec.participation_rate = 0.0
            except AttributeError:
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
        """AI Feature 3: Gathers all self-reported impacts and generates a 3-sentence summary using Grok."""
        self.ensure_one()
        
        # 1. Gather all approved impacts
        approved_parts = self.participation_ids.filtered(lambda p: p.approval_status == 'approved' and p.self_reported_impact)
        impact_texts = [p.self_reported_impact for p in approved_parts]
        
        # 2. Guard against empty lists to save API calls
        if not impact_texts:
            self.message_post(body="✅ Activity marked as completed. *(AI Summary skipped: No self-reported impact data was provided by participants)*")
            return
            
        combined_text = "\n".join(f"- {text}" for text in impact_texts)
        
        # 3. Formulate the precise 3-sentence prompt
        prompt = (
            f"You are an ESG analyst. We just finished the CSR activity '{self.name}'. "
            f"Here are the impact descriptions provided by the participants:\n"
            f"{combined_text}\n\n"
            f"Write a concise, exactly 3-sentence summary of the overall impact achieved. "
            f"Do not include quotes, markdown fences, or any other introductory text."
        )
        
        api_key = self.env['ir.config_parameter'].sudo().get_param('ecosphere.grok_api_key')
        if not api_key:
            self.message_post(body="✅ Activity completed. *(AI Summary skipped: Missing API Key)*")
            return
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-beta",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }
        
        try:
            import requests
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            response.raise_for_status()
            res_text = response.json()['choices'][0]['message']['content'].strip()
            
            # 4. Save and announce
            self.ai_summary = res_text
            self.message_post(body=f"<b>🤖 AI Impact Summary:</b><br/>{res_text}")
            
        except Exception as e:
            _logger.error(f"AI Summary generation failed: {str(e)}")
            self.message_post(body="✅ Activity completed. *(AI Summary generation failed)*")
