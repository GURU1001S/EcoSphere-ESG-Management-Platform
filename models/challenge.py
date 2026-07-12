# -*- coding: utf-8 -*-
import json
import logging
import datetime
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class EcoChallenge(models.Model):
    _name = 'eco.challenge'
    _description = 'ESG Challenge'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, tracking=True)
    category_id = fields.Many2one('eco.category', string='Category', domain=[('type', '=', 'challenge')], tracking=True)
    description = fields.Text(string='Description')
    xp_reward = fields.Integer(string='Base XP Reward', default=0, tracking=True)
    difficulty = fields.Selection([
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], string='Difficulty', default='easy', tracking=True)
    evidence_required = fields.Boolean(string='Evidence Required', default=False, tracking=True)
    deadline = fields.Date(string='Deadline', tracking=True)
    department_id = fields.Many2one('eco.department', string='Department', tracking=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('under_review', 'Under Review'),
        ('completed', 'Completed'),
        ('archived', 'Archived')
    ], string='Status', default='draft', required=True, tracking=True)
    
    participation_ids = fields.One2many('eco.challenge.participation', 'challenge_id', string='Participations')

    # R&D Intelligence Additions
    completion_rate = fields.Float(string='Completion Rate (%)', compute='_compute_completion_metrics', store=True)
    avg_completion_days = fields.Float(string='Avg Completion Days', compute='_compute_completion_metrics', store=True)
    dynamic_xp = fields.Integer(string='Dynamic XP', compute='_compute_dynamic_xp', store=True)
    ai_generated = fields.Boolean(string='AI Generated', default=False, tracking=True)
    ai_rationale = fields.Text(string='AI Rationale')
    recommended_for_ids = fields.Many2many('hr.employee', string='Recommended For')

    @api.depends('participation_ids.approval_status', 'participation_ids.create_date', 'participation_ids.completion_date')
    def _compute_completion_metrics(self):
        for challenge in self:
            parts = challenge.participation_ids
            total = len(parts)
            
            # Safely filter relying on challenge_participation.py definitions
            try:
                approved = parts.filtered(lambda p: p.approval_status == 'approved')
                approved_count = len(approved)
            except AttributeError:
                approved = self.env['eco.challenge.participation']
                approved_count = 0

            challenge.completion_rate = (approved_count / float(total)) * 100.0 if total > 0 else 0.0

            total_days = 0
            count_days = 0
            for p in approved:
                start = p.create_date.date() if p.create_date else False
                end = getattr(p, 'completion_date', False)
                if start and end and end >= start:
                    total_days += (end - start).days
                    count_days += 1
            
            challenge.avg_completion_days = (total_days / float(count_days)) if count_days > 0 else 0.0

    @api.depends('xp_reward', 'difficulty', 'completion_rate')
    def _compute_dynamic_xp(self):
        for challenge in self:
            multiplier = 1.0
            if challenge.difficulty == 'medium':
                multiplier = 1.3
            elif challenge.difficulty == 'hard':
                multiplier = 1.6
                
            base = challenge.xp_reward * multiplier
            
            # Self-balancing incentive system
            if challenge.completion_rate > 0:
                if challenge.completion_rate < 20.0:
                    base = base * 1.2   # Too hard -> Increase reward
                elif challenge.completion_rate > 80.0:
                    base = base * 0.8   # Too easy -> Decrease reward
                    
            challenge.dynamic_xp = int(base)

    def action_activate(self):
        for rec in self:
            rec.status = 'active'
        return True

    def action_submit(self):
        for rec in self:
            rec.status = 'under_review'
        return True

    def action_complete(self):
        for rec in self:
            rec.status = 'completed'
        return True

    def action_archive(self):
        for rec in self:
            rec.status = 'archived'
        return True

    @api.model
    def _call_ai(self, prompt):
        api_key = self.env['ir.config_parameter'].sudo().get_param('ecosphere.grok_api_key')
        if not api_key:
            raise UserError("Grok API key is missing. Please add 'ecosphere.grok_api_key' in Settings > System Parameters.")
            
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-beta",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            res_json = response.json()
            return res_json['choices'][0]['message']['content']
        except Exception as e:
            _logger.error(f"Grok API failed: {str(e)}")
            raise UserError(f"Failed to communicate with Grok API: {str(e)}")

    def action_ai_generate(self):
        department = False
        if self and getattr(self[0], 'department_id', False):
            department = self[0].department_id
        else:
            active_id = self.env.context.get('active_id')
            active_model = self.env.context.get('active_model')
            if active_model == 'eco.department' and active_id:
                department = self.env['eco.department'].browse(active_id)
            if not department:
                emp = self.env.user.employee_id
                department = getattr(emp, 'department_id', False)
                if not department:
                    department = self.env['eco.department'].search([], limit=1)
                    
        if not department:
            raise UserError("No department found to analyze.")
            
        env_s = getattr(department, 'env_score', 0)
        soc_s = getattr(department, 'social_score', 0)
        gov_s = getattr(department, 'gov_score', 0)
        
        weakest = "Unknown"
        if hasattr(department, '_get_weakest_pillar'):
            try:
                weakest = department._get_weakest_pillar()
            except Exception:
                pass
                
        prompt = (
            f"You are an ESG expert. The '{department.name}' department has scores: "
            f"Environmental: {env_s}, Social: {soc_s}, Governance: {gov_s}. "
            f"Their weakest pillar is {weakest}. "
            f"Generate exactly 3 new challenges targeting this weakness. "
            f"Respond strictly in JSON format as an array of 3 objects with keys: "
            f"'name', 'description', 'xp_reward' (integer between 10-100), 'difficulty' ('easy', 'medium', or 'hard'), and 'ai_rationale' (string explaining why). "
            f"Do not include markdown fences or other text."
        )
        
        res_text = self._call_ai(prompt)
        
        res_text = res_text.strip()
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        elif res_text.startswith("```"):
            res_text = res_text[3:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]
        res_text = res_text.strip()
        
        try:
            data = json.loads(res_text)
        except Exception as e:
            _logger.error(f"Failed to parse Grok JSON. Raw response:\n{res_text}")
            raise UserError(f"Grok returned invalid JSON. Raw response logged. Error: {str(e)}")
            
        if not isinstance(data, list):
            raise UserError("Grok did not return a JSON array.")
            
        created = self.env['eco.challenge']
        for item in data:
            vals = {
                'name': item.get('name', 'AI Generated Challenge'),
                'description': item.get('description', ''),
                'xp_reward': int(item.get('xp_reward', 20)),
                'difficulty': item.get('difficulty', 'medium'),
                'ai_rationale': item.get('ai_rationale', ''),
                'ai_generated': True,
                'status': 'draft',
                'department_id': department.id
            }
            created |= self.create(vals)
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AI Challenges Generated',
                'message': f'Successfully generated 3 draft challenges for {department.name}.',
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
            }
        }


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    xp = fields.Integer(string='XP', default=0, tracking=True)
    points = fields.Integer(string='Points', default=0, tracking=True)
    badge_ids = fields.Many2many('eco.badge', string='Badges')
    
    challenge_participation_ids = fields.One2many('eco.challenge.participation', 'employee_id', string='Participations')
    
    # NOTE: These compute fields depend on challenge_participation.py existing!
    completed_challenge_count = fields.Integer(string='Completed Challenges', compute='_compute_completed_challenge_count', store=True)
    streak = fields.Integer(string='Streak (Weeks)', compute='_compute_streak', store=True)
    
    sentiment_tag = fields.Selection([
        ('inactive', 'Inactive'),
        ('struggling', 'Struggling'),
        ('consistent', 'Consistent'),
        ('motivated', 'Motivated'),
        ('champion', 'Champion')
    ], string='Sentiment Tag', default='inactive', tracking=True)
    
    sustainability_archetype = fields.Char(string='Sustainability Archetype', compute='_compute_archetype')
    
    strongest_pillar = fields.Selection([
        ('environmental', 'Environmental'),
        ('social', 'Social'),
        ('governance', 'Governance')
    ], string='Strongest Pillar')
    
    recommended_challenge_ids = fields.Many2many('eco.challenge', string='Recommended Challenges')

    def _compute_archetype(self):
        for emp in self:
            emp.sustainability_archetype = "The Contributor"

    @api.depends('challenge_participation_ids.approval_status')
    def _compute_completed_challenge_count(self):
        for emp in self:
            try:
                emp.completed_challenge_count = len(emp.challenge_participation_ids.filtered(lambda p: p.approval_status == 'approved'))
            except AttributeError:
                emp.completed_challenge_count = 0

    @api.depends('challenge_participation_ids.approval_status', 'challenge_participation_ids.completion_date')
    def _compute_streak(self):
        for emp in self:
            try:
                approved = emp.challenge_participation_ids.filtered(lambda p: p.approval_status == 'approved' and p.completion_date)
                if not approved:
                    emp.streak = 0
                    continue
                    
                dates = sorted([p.completion_date for p in approved], reverse=True)
                
                streak = 1
                current_week = dates[0].isocalendar()[1]
                current_year = dates[0].isocalendar()[0]
                
                for d in dates[1:]:
                    w = d.isocalendar()[1]
                    y = d.isocalendar()[0]
                    
                    if y == current_year and w == current_week:
                        continue 
                    elif (y == current_year and w == current_week - 1) or (y == current_year - 1 and current_week == 1 and w in (52, 53)):
                        streak += 1
                        current_week = w
                        current_year = y
                    else:
                        break
                emp.streak = streak
            except AttributeError:
                emp.streak = 0

    def action_recommend_challenges(self):
        for emp in self:
            active_challenges = self.env['eco.challenge'].search([('status', '=', 'active')])
            try:
                completed = emp.challenge_participation_ids.filtered(lambda p: p.approval_status == 'approved').mapped('challenge_id')
                available = active_challenges - completed
            except AttributeError:
                available = active_challenges
                
            if not available:
                raise UserError("No active challenges available to recommend.")
                
            challenge_list = "\n".join([f"- ID {c.id}: {c.name} (Difficulty: {c.difficulty}, XP: {c.dynamic_xp or c.xp_reward})" for c in available])
            
            prompt = (
                f"You are an AI career coach. Recommend the top 3 challenges for employee '{emp.name}' "
                f"who has a sentiment of '{emp.sentiment_tag}' and strongest pillar '{emp.strongest_pillar}'.\n"
                f"Here are the available challenges:\n{challenge_list}\n"
                f"Respond strictly in JSON format as a list of integers representing the IDs of the 3 recommended challenges. "
                f"Example: [1, 5, 8]. No markdown."
            )
            
            res_text = self.env['eco.challenge']._call_ai(prompt)
            
            res_text = res_text.strip()
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            elif res_text.startswith("```"):
                res_text = res_text[3:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]
            res_text = res_text.strip()
            
            try:
                data = json.loads(res_text)
            except Exception as e:
                _logger.error(f"Grok JSON Error: {res_text}")
                raise UserError("Grok returned invalid JSON.")
                
            if not isinstance(data, list):
                raise UserError("Expected a list of IDs from Grok.")
                
            emp.recommended_challenge_ids = [(6, 0, data)]
            
        return True
