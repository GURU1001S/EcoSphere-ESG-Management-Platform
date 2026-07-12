from odoo import models, fields, api

# Maps esg.environmental.goal's status field to a numeric score,
# since there is no current-vs-target progress field to compute a percentage from.
GOAL_STATUS_SCORE = {
    'achieved': 100.0,
    'on_track': 60.0,
    'at_risk': 20.0,
}


class DepartmentScore(models.Model):
    _name = 'esg.department.score'
    _description = 'Aggregated ESG Score per Department'
    _inherit = ['mail.thread']
    _order = 'period_date desc'
    _rec_name = 'department_id'

    department_id = fields.Many2one('esg.department', required=True, ondelete='cascade', tracking=True)
    period_date = fields.Date(required=True, default=fields.Date.today, tracking=True)

    environmental_score = fields.Float(default=0.0, tracking=True)
    social_score = fields.Float(default=0.0, tracking=True)
    governance_score = fields.Float(default=0.0, tracking=True)
    total_score = fields.Float(compute='_compute_total_score', store=True, tracking=True)

    _sql_constraints = [
        ('department_period_unique', 'unique(department_id, period_date)',
         'Only one score snapshot per department per period.')
    ]

    @api.depends('environmental_score', 'social_score', 'governance_score')
    def _compute_total_score(self):
        config = self.env['ir.config_parameter'].sudo()
        env_weight = float(config.get_param('ecosphere.weight_environmental', default=40)) / 100.0
        soc_weight = float(config.get_param('ecosphere.weight_social', default=30)) / 100.0
        gov_weight = float(config.get_param('ecosphere.weight_governance', default=30)) / 100.0
        for rec in self:
            rec.total_score = (
                rec.environmental_score * env_weight +
                rec.social_score * soc_weight +
                rec.governance_score * gov_weight
            )

    @api.model
    def _compute_environmental_score(self, department):
        """Score emissions against department goals, with status as fallback."""
        Goal = self.env['esg.environmental.goal']
        Carbon = self.env['carbon.transaction']
        goals = Goal.search([('department_id', '=', department.id)])
        if not goals:
            return 0.0

        scores = []
        for goal in goals:
            domain = [('department_id', '=', department.id)]
            if goal.deadline:
                domain.append(('date', '<=', goal.deadline))
            emissions = sum(Carbon.search(domain).mapped('total_emission'))
            if goal.target_emission > 0:
                ratio = emissions / goal.target_emission
                scores.append(max(0.0, min(100.0, 100.0 - (ratio * 100.0))))
            else:
                scores.append(GOAL_STATUS_SCORE.get(goal.status, 0.0))
        return sum(scores) / len(scores) if scores else 0.0

    @api.model
    def _compute_social_score(self, department):
        """CSR participation approval rate, employees looked up via esg_department_id bridge field."""
        Participation = self.env['esg.employee.participation']
        employees = self.env['hr.employee'].search([('esg_department_id', '=', department.id)])
        if not employees:
            return 0.0
        total = Participation.search_count([('employee_id', 'in', employees.ids)])
        approved = Participation.search_count([
            ('employee_id', 'in', employees.ids),
            ('approval_status', '=', 'approved'),
        ])
        return (approved / total * 100.0) if total else 0.0

    @api.model
    def _compute_governance_score(self, department):
        Ack = self.env['esg.policy.acknowledgement']
        Issue = self.env['esg.compliance.issue']

        acks = Ack.search([('department_id', '=', department.id)])
        total_acks = len(acks)
        acked = len(acks.filtered(lambda a: a.state == 'acknowledged'))
        ack_rate = (acked / total_acks * 100.0) if total_acks else 100.0

        severity_weight = {'low': 2, 'medium': 5, 'high': 10, 'critical': 20}
        open_issues = Issue.search([
            ('department_id', '=', department.id),
            ('status', '!=', 'resolved'),
        ])
        penalty = sum(severity_weight.get(i.severity, 5) for i in open_issues)

        return max(0.0, min(100.0, ack_rate - penalty))

    @api.model
    def recompute_department_score(self, department, period_date=None):
        period_date = period_date or fields.Date.today()
        env_score = self._compute_environmental_score(department)
        soc_score = self._compute_social_score(department)
        gov_score = self._compute_governance_score(department)

        existing = self.search([
            ('department_id', '=', department.id),
            ('period_date', '=', period_date),
        ], limit=1)
        vals = {
            'department_id': department.id,
            'period_date': period_date,
            'environmental_score': env_score,
            'social_score': soc_score,
            'governance_score': gov_score,
        }
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def _cron_recompute_all_scores(self):
        departments = self.env['esg.department'].search([])
        for dept in departments:
            self.recompute_department_score(dept)

    @api.model
    def get_overall_esg_score(self):
        departments = self.env['esg.department'].search([])
        scores = []
        for dept in departments:
            latest = self.search(
                [('department_id', '=', dept.id)], order='period_date desc', limit=1
            )
            if latest:
                scores.append(latest.total_score)
        return sum(scores) / len(scores) if scores else 0.0
