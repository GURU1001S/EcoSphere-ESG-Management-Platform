# -*- coding: utf-8 -*-
import random
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    """ESG extensions on hr.employee — single inheritance file for the module."""

    _inherit = 'hr.employee'

    esg_department_id = fields.Many2one('esg.department', string='ESG Department', tracking=True)
    xp = fields.Integer(string='XP', default=0, tracking=True)
    points = fields.Integer(string='Points', default=0, tracking=True)
    badge_ids = fields.Many2many(
        'esg.badge',
        'esg_badge_employee_rel',
        'employee_id',
        'badge_id',
        string='Badges',
    )
    challenge_participation_ids = fields.One2many(
        'esg.challenge.participation', 'employee_id', string='Challenge Participations'
    )
    completed_challenge_count = fields.Integer(
        string='Completed Challenges',
        compute='_compute_completed_challenge_count', store=True,
    )
    streak = fields.Integer(
        string='Streak (Weeks)', compute='_compute_streak', store=True,
    )
    sentiment_tag = fields.Selection(
        [
            ('inactive', 'Inactive'),
            ('struggling', 'Struggling'),
            ('consistent', 'Consistent'),
            ('motivated', 'Motivated'),
            ('champion', 'Champion'),
        ],
        string='Sentiment Tag', default='inactive', tracking=True,
    )
    sustainability_archetype = fields.Char(
        string='Sustainability Archetype', compute='_compute_archetype', store=True,
    )
    strongest_pillar = fields.Selection(
        [
            ('environmental', 'Environmental'),
            ('social', 'Social'),
            ('governance', 'Governance'),
        ],
        string='Strongest Pillar',
        compute='_compute_strongest_pillar', store=True,
    )
    recommended_challenge_ids = fields.Many2many(
        'esg.challenge',
        'esg_challenge_recommendation_rel',
        'employee_id',
        'challenge_id',
        string='Recommended Challenges',
    )
    engagement_score = fields.Float(
        string='Engagement Score', compute='_compute_engagement_score', store=True,
    )

    @api.depends(
        'challenge_participation_ids.approval_status',
        'challenge_participation_ids.challenge_id.category_id',
        'xp', 'completed_challenge_count', 'streak',
    )
    def _compute_archetype(self):
        for emp in self:
            if emp.completed_challenge_count == 0 and emp.xp == 0:
                emp.sustainability_archetype = 'The Quiet Contributor'
            elif emp.streak >= 4:
                emp.sustainability_archetype = 'The Department Anchor'
            elif emp.completed_challenge_count >= 3 and emp.streak <= 1:
                emp.sustainability_archetype = 'The Sprint Hero'
            else:
                # Category specialist if >50% of completions share a category
                approved = emp.challenge_participation_ids.filtered(
                    lambda p: p.approval_status == 'approved'
                )
                counts = {}
                for part in approved:
                    cat = part.challenge_id.category_id
                    if cat:
                        counts[cat.id] = counts.get(cat.id, 0) + 1
                total = len(approved) or 1
                if counts and max(counts.values()) / total >= 0.5:
                    emp.sustainability_archetype = 'The Category Specialist'
                else:
                    emp.sustainability_archetype = 'The Contributor'

    @api.depends('challenge_participation_ids.approval_status')
    def _compute_completed_challenge_count(self):
        for emp in self:
            emp.completed_challenge_count = len(
                emp.challenge_participation_ids.filtered(
                    lambda p: p.approval_status == 'approved'
                )
            )

    @api.depends(
        'challenge_participation_ids.approval_status',
        'challenge_participation_ids.completion_date',
    )
    def _compute_streak(self):
        for emp in self:
            approved = emp.challenge_participation_ids.filtered(
                lambda p: p.approval_status == 'approved' and p.completion_date
            )
            if not approved:
                emp.streak = 0
                continue
            dates = sorted([p.completion_date for p in approved], reverse=True)
            streak = 1
            current_week = dates[0].isocalendar()[1]
            current_year = dates[0].isocalendar()[0]
            for d in dates[1:]:
                w, y = d.isocalendar()[1], d.isocalendar()[0]
                if y == current_year and w == current_week:
                    continue
                if (y == current_year and w == current_week - 1) or (
                    y == current_year - 1 and current_week == 1 and w in (52, 53)
                ):
                    streak += 1
                    current_week, current_year = w, y
                else:
                    break
            emp.streak = streak

    @api.depends(
        'challenge_participation_ids.approval_status',
        'challenge_participation_ids.challenge_id',
    )
    def _compute_strongest_pillar(self):
        # Map challenge category names heuristically when no explicit pillar
        for emp in self:
            approved = emp.challenge_participation_ids.filtered(
                lambda p: p.approval_status == 'approved'
            )
            if not approved:
                emp.strongest_pillar = False
                continue
            # Default environmental for most challenges; use category name keywords
            scores = {'environmental': 0, 'social': 0, 'governance': 0}
            for part in approved:
                name = (part.challenge_id.category_id.name or part.challenge_id.name or '').lower()
                if any(k in name for k in ('social', 'volunteer', 'wellness', 'community')):
                    scores['social'] += 1
                elif any(k in name for k in ('govern', 'policy', 'audit', 'compliance', 'security')):
                    scores['governance'] += 1
                else:
                    scores['environmental'] += 1
            emp.strongest_pillar = max(scores, key=scores.get)

    @api.depends(
        'completed_challenge_count', 'streak', 'xp',
        'challenge_participation_ids.engagement_score',
    )
    def _compute_engagement_score(self):
        for emp in self:
            parts = emp.challenge_participation_ids.filtered(
                lambda p: p.approval_status == 'approved'
            )
            avg_eng = (
                sum(parts.mapped('engagement_score')) / len(parts) if parts else 0.0
            )
            # Normalize to 0–100: quality (avg eng 0–10) × frequency × streak boost
            freq = min(emp.completed_challenge_count, 10) * 5  # max 50
            quality = avg_eng * 3  # max 30
            consistency = min(emp.streak, 4) * 5  # max 20
            emp.engagement_score = min(100.0, freq + quality + consistency)

    def action_recommend_challenges(self):
        for emp in self:
            active = self.env['esg.challenge'].search([('status', '=', 'active')])
            completed = emp.challenge_participation_ids.filtered(
                lambda p: p.approval_status == 'approved'
            ).mapped('challenge_id')
            available = active - completed
            if not available:
                raise UserError('No active challenges available to recommend.')

            # Prefer challenges matching strongest pillar / department
            preferred = available
            if emp.esg_department_id:
                dept_match = available.filtered(
                    lambda c: not c.department_id or c.department_id == emp.esg_department_id
                )
                if dept_match:
                    preferred = dept_match

            ids = preferred.ids
            random.shuffle(ids)
            emp.recommended_challenge_ids = [(6, 0, ids[:3])]
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recommendations Ready',
                'message': 'Up to 3 challenges recommended for this employee.',
                'type': 'success',
                'sticky': False,
            },
        }
