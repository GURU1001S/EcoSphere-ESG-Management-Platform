# -*- coding: utf-8 -*-
import json
import logging
import datetime
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class EcoChallenge(models.Model):
    _name = 'esg.challenge'
    _description = 'ESG Challenge'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, tracking=True)
    category_id = fields.Many2one('esg.category', string='Category', domain=[('type', '=', 'challenge')], tracking=True)
    description = fields.Text(string='Description')
    xp_reward = fields.Integer(string='Base XP Reward', default=0, tracking=True)
    difficulty = fields.Selection([
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], string='Difficulty', default='easy', tracking=True)
    evidence_required = fields.Boolean(string='Evidence Required', default=False, tracking=True)
    deadline = fields.Date(string='Deadline', tracking=True)
    department_id = fields.Many2one('esg.department', string='Department', tracking=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('under_review', 'Under Review'),
        ('completed', 'Completed'),
        ('archived', 'Archived')
    ], string='Status', default='draft', required=True, tracking=True)
    
    participation_ids = fields.One2many('esg.challenge.participation', 'challenge_id', string='Participations')

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
                approved = self.env['esg.challenge.participation']
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

    def action_ai_generate(self):
        department = False
        if self and getattr(self[0], 'department_id', False):
            department = self[0].department_id
        else:
            active_id = self.env.context.get('active_id')
            active_model = self.env.context.get('active_model')
            if active_model == 'esg.department' and active_id:
                department = self.env['esg.department'].browse(active_id)
            if not department:
                emp = self.env.user.employee_id
                department = getattr(emp, 'esg_department_id', False) or getattr(emp, 'department_id', False)
                if not department:
                    department = self.env['esg.department'].search([], limit=1)
                    
        if not department:
            raise UserError("No department found to analyze.")
            
        score_rec = self.env['esg.department.score'].search([('department_id', '=', department.id)], order='period_date desc', limit=1)
        if not score_rec:
            env_s, soc_s, gov_s = 0, 0, 0
        else:
            env_s = score_rec.environmental_score
            soc_s = score_rec.social_score
            gov_s = score_rec.governance_score
            
        scores = {'Environmental': env_s, 'Social': soc_s, 'Governance': gov_s}
        weakest = min(scores, key=scores.get) if any(scores.values()) else 'Environmental'
        
        templates = {
            'Environmental': [
                {'name': 'Reduce Paper Waste', 'description': 'Print 50% less pages this week.', 'xp_reward': 30, 'difficulty': 'easy'},
                {'name': 'Energy Saver', 'description': 'Turn off all monitors before leaving for 5 days.', 'xp_reward': 40, 'difficulty': 'medium'},
                {'name': 'Zero Waste Lunch', 'description': 'Bring lunch in reusable containers for a week.', 'xp_reward': 50, 'difficulty': 'hard'}
            ],
            'Social': [
                {'name': 'Community Volunteer', 'description': 'Log 2 hours of volunteering.', 'xp_reward': 60, 'difficulty': 'medium'},
                {'name': 'Wellness Walk', 'description': 'Participate in the department wellness walk.', 'xp_reward': 20, 'difficulty': 'easy'},
                {'name': 'Mentorship Session', 'description': 'Host a 1 hour mentorship session.', 'xp_reward': 80, 'difficulty': 'hard'}
            ],
            'Governance': [
                {'name': 'Policy Review', 'description': 'Review and acknowledge all pending policies.', 'xp_reward': 30, 'difficulty': 'easy'},
                {'name': 'Security Training', 'description': 'Complete the cybersecurity module with 100%.', 'xp_reward': 50, 'difficulty': 'medium'},
                {'name': 'Audit Prep', 'description': 'Assist in organizing files for the upcoming audit.', 'xp_reward': 100, 'difficulty': 'hard'}
            ]
        }
        
        data = templates.get(weakest, templates['Environmental'])
        
        created = self.env['esg.challenge']
        for item in data:
            vals = {
                'name': item['name'],
                'description': item['description'],
                'xp_reward': item['xp_reward'],
                'difficulty': item['difficulty'],
                'ai_rationale': f'System generated to target weakest pillar: {weakest}.',
                'ai_generated': True,
                'status': 'draft',
                'department_id': department.id
            }
            created |= self.create(vals)
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Challenges Generated',
                'message': f'Successfully generated 3 draft {weakest} challenges for {department.name}.',
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
            }
        }


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    esg_department_id = fields.Many2one('esg.department', string='ESG Department')
    xp = fields.Integer(string='XP', default=0, tracking=True)
    points = fields.Integer(string='Points', default=0, tracking=True)
    badge_ids = fields.Many2many('esg.badge', string='Badges')
    
    challenge_participation_ids = fields.One2many('esg.challenge.participation', 'employee_id', string='Participations')
    
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
    
    recommended_challenge_ids = fields.Many2many('esg.challenge', string='Recommended Challenges')

    def _compute_archetype(self):
        for emp in self:
            approved = emp.challenge_participation_ids.filtered(lambda p: p.approval_status == 'approved')
            if not approved:
                emp.sustainability_archetype = "The Quiet Contributor"
            elif emp.streak >= 3:
                emp.sustainability_archetype = "The Sprint Hero"
            elif emp.strongest_pillar:
                emp.sustainability_archetype = "The Category Specialist"
            elif emp.esg_department_id:
                dept_employees = self.env['hr.employee'].search([
                    ('esg_department_id', '=', emp.esg_department_id.id)
                ])
                max_xp = max(dept_employees.mapped('xp') or [0])
                emp.sustainability_archetype = (
                    "The Department Anchor" if emp.xp >= max_xp and emp.xp > 0 else "The Contributor"
                )
            else:
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
            active_challenges = self.env['esg.challenge'].search([('status', '=', 'active')])
            try:
                completed = emp.challenge_participation_ids.filtered(lambda p: p.approval_status == 'approved').mapped('challenge_id')
                available = active_challenges - completed
            except AttributeError:
                available = active_challenges
                
            if not available:
                raise UserError("No active challenges available to recommend.")

            pillar = emp.strongest_pillar
            if not pillar and emp.esg_department_id:
                score = self.env['esg.department.score'].search([
                    ('department_id', '=', emp.esg_department_id.id)
                ], order='period_date desc', limit=1)
                if score:
                    pillars = {
                        'environmental': score.environmental_score,
                        'social': score.social_score,
                        'governance': score.governance_score,
                    }
                    pillar = min(pillars, key=pillars.get)

            preferred_difficulty = {
                'inactive': 'easy',
                'struggling': 'easy',
                'consistent': 'medium',
                'motivated': 'medium',
                'champion': 'hard',
            }.get(emp.sentiment_tag, 'easy')

            def challenge_score(challenge):
                score = 0
                if challenge.difficulty == preferred_difficulty:
                    score += 3
                if pillar and challenge.category_id and challenge.category_id.type == 'challenge':
                    text = f"{challenge.name} {challenge.description or ''} {challenge.category_id.name or ''}".lower()
                    if pillar in text:
                        score += 4
                if emp.esg_department_id and challenge.department_id == emp.esg_department_id:
                    score += 2
                return score

            data = available.sorted(key=challenge_score, reverse=True)[:3].ids
            emp.recommended_challenge_ids = [(6, 0, data)]
            
        return True
