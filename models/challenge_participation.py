# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class EcoChallengeParticipation(models.Model):
    _name = 'eco.challenge.participation'
    _description = 'Challenge Participation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    challenge_id = fields.Many2one('eco.challenge', string='Challenge', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    progress = fields.Integer(string='Progress (%)', default=0, tracking=True)
    proof = fields.Binary(string='Proof File')
    proof_filename = fields.Char(string='Proof Filename')
    
    approval_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='pending', tracking=True)
    
    xp_awarded = fields.Integer(string='XP Awarded', default=0, tracking=True)
    completion_date = fields.Date(string='Completion Date')

    # R&D Extensions
    started_date = fields.Date(string='Started On', default=fields.Date.context_today, tracking=True)
    submitted_date = fields.Date(string='Submitted On', tracking=True)
    
    days_to_complete = fields.Integer(string='Days to Complete', compute='_compute_days', store=True)
    attempt_number = fields.Integer(string='Attempt Number', compute='_compute_attempt_number')
    
    engagement_score = fields.Integer(string='Engagement Score', compute='_compute_engagement_score', store=True)
    ai_feedback = fields.Text(string='AI Feedback')
    
    sentiment_tag = fields.Selection([
        ('motivated', 'Motivated'),
        ('struggling', 'Struggling'),
        ('consistent', 'Consistent'),
        ('inactive', 'Inactive')
    ], string='Sentiment Tag')

    @api.depends('started_date', 'submitted_date')
    def _compute_days(self):
        for rec in self:
            if rec.started_date and rec.submitted_date:
                rec.days_to_complete = (rec.submitted_date - rec.started_date).days
            else:
                rec.days_to_complete = 0

    def _compute_attempt_number(self):
        for rec in self:
            if rec.employee_id and rec.challenge_id:
                domain = [
                    ('employee_id', '=', rec.employee_id.id),
                    ('challenge_id', '=', rec.challenge_id.id),
                ]
                if rec.id:
                    domain.append(('id', '<', rec.id))
                rec.attempt_number = self.env['eco.challenge.participation'].search_count(domain) + 1
            else:
                rec.attempt_number = 1

    @api.depends('submitted_date', 'started_date', 'proof', 'challenge_id.deadline')
    def _compute_engagement_score(self):
        """
        Simple scoring (0-10): 
        +5 if proof attached
        +5 if submitted within half the deadline window
        """
        for rec in self:
            score = 0
            if rec.proof:
                score += 5
                
            if rec.submitted_date and rec.started_date and rec.challenge_id.deadline:
                total_window = (rec.challenge_id.deadline - rec.started_date).days
                if total_window > 0:
                    days_taken = (rec.submitted_date - rec.started_date).days
                    if days_taken <= (total_window / 2):
                        score += 5
            rec.engagement_score = score

    def action_submit_proof(self):
        """Action for the employee to submit their proof."""
        for rec in self:
            rec.submitted_date = fields.Date.context_today(self)
        return True

    def action_approve(self):
        for rec in self:
            rec.approval_status = 'approved'
        return True

    def action_reject(self):
        for rec in self:
            rec.approval_status = 'rejected'
        return True

    def write(self, vals):
        """Intercept write to detect state changes cleanly and prevent duplicate XP awards."""
        status_changed = 'approval_status' in vals
        old_statuses = {rec.id: rec.approval_status for rec in self} if status_changed else {}
        
        res = super(EcoChallengeParticipation, self).write(vals)
        
        if status_changed:
            for rec in self:
                if rec.approval_status == 'approved' and old_statuses.get(rec.id) != 'approved':
                    rec._handle_approval()
                elif rec.approval_status == 'rejected' and old_statuses.get(rec.id) != 'rejected':
                    rec._handle_rejection()
        return res

    def _handle_approval(self):
        self.ensure_one()
        
        # 1. Dates and XP
        if not self.completion_date:
            self.completion_date = fields.Date.context_today(self)
        if not self.submitted_date:
            self.submitted_date = fields.Date.context_today(self)

        xp_to_award = self.challenge_id.dynamic_xp or self.challenge_id.xp_reward
        self.xp_awarded = xp_to_award
        
        if self.employee_id:
            self.employee_id.xp += xp_to_award
            
            # Update employee sentiment heuristically without API call
            if self.engagement_score >= 8:
                self.employee_id.sentiment_tag = 'motivated'
                self.sentiment_tag = 'motivated'
            elif self.engagement_score <= 3 and self.attempt_number >= 2:
                self.employee_id.sentiment_tag = 'struggling'
                self.sentiment_tag = 'struggling'
            else:
                self.employee_id.sentiment_tag = 'consistent'
                self.sentiment_tag = 'consistent'
            
            # Badge unlock routine
            config = self.env['ir.config_parameter'].sudo()
            auto_award = config.get_param('ecosphere.badge_auto_award', False)
            
            if auto_award:
                unlocked_badges = self.env['eco.badge'].search([('employee_ids', '!=', self.employee_id.id)])
                for badge in unlocked_badges:
                    if badge.check_unlock(self.employee_id):
                        badge.employee_ids = [(4, self.employee_id.id)]
                        self.employee_id.message_post(
                            body=f"🏆 Congratulations! You unlocked the <b>{badge.name}</b> badge!"
                        )
                
                # Early Adopter Check
                approved_count = self.search_count([
                    ('challenge_id', '=', self.challenge_id.id),
                    ('approval_status', '=', 'approved')
                ])
                if approved_count <= 10:
                    early_badge = self.env['eco.badge'].search([('unlock_rule', '=', 'early_adopter')], limit=1)
                    if early_badge and self.employee_id.id not in early_badge.employee_ids.ids:
                        early_badge.employee_ids = [(4, self.employee_id.id)]
                        self.employee_id.message_post(
                            body=f"🚀 You are an Early Adopter! You unlocked the <b>{early_badge.name}</b> badge!"
                        )
        
        # Generate Grok AI Feedback
        self._generate_ai_feedback()
        
    def _handle_rejection(self):
        self.ensure_one()
        partner_ids = [self.employee_id.user_id.partner_id.id] if self.employee_id and self.employee_id.user_id else []
        self.message_post(
            body=f"Your participation in '{self.challenge_id.name}' was rejected. Please review the requirements and submit new proof.",
            partner_ids=partner_ids
        )
        
    def _generate_ai_feedback(self):
        """Calls Grok API to generate a personalized motivational message."""
        api_key = self.env['ir.config_parameter'].sudo().get_param('ecosphere.grok_api_key')
        if not api_key:
            self.message_post(body="✅ Participation approved. *(AI Feedback disabled: Missing API Key)*")
            return
            
        prompt = (
            f"You are a motivational ESG coach. Employee '{self.employee_id.name}' just completed the "
            f"challenge '{self.challenge_id.name}' and earned {self.xp_awarded} XP. "
            f"Their engagement score was {self.engagement_score}/10 on this task. "
            f"Write a short, engaging, 2-3 sentence motivational feedback paragraph to congratulate them. "
            f"Do not include quotes or markdown blocks, just the raw text."
        )
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        try:
            import requests
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            res_text = response.json()['choices'][0]['message']['content'].strip()
            
            self.ai_feedback = res_text
            
            partner_ids = [self.employee_id.user_id.partner_id.id] if self.employee_id and self.employee_id.user_id else []
            self.message_post(
                body=f"<b>AI Coach:</b><br/>{res_text}",
                partner_ids=partner_ids
            )
        except Exception as e:
            _logger.error(f"Failed Grok AI Feedback: {str(e)}")
            self.ai_feedback = "Great job completing the challenge!"
            self.message_post(body="✅ Participation approved. *(AI Feedback currently unavailable)*")
