from odoo import models, fields, api


class DepartmentScore(models.Model):
    _name = 'eco.department.score'
    _description = 'Aggregated ESG Score per Department'
    _inherit = ['mail.thread']
    _order = 'period_date desc'
    _rec_name = 'department_id'

    department_id = fields.Many2one('eco.department', required=True, ondelete='cascade', tracking=True)
    period_date = fields.Date(required=True, default=fields.Date.today, tracking=True,
                               help="The date this score snapshot represents (e.g. month-end)")

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

    # ---------------------------------------------------------
    # Scoring Engine — recompute methods
    # ---------------------------------------------------------

    @api.model
    def _compute_environmental_score(self, department):
        """Based on Environmental Goal progress (goal fields owned by Person A)."""
        Goal = self.env['eco.environmental.goal']
        goals = Goal.search([('department_id', '=', department.id)])
        if not goals:
            return 0.0
        progresses = []
        for goal in goals:
            if goal.target_co2:
                pct = max(0.0, min(100.0, 100.0 * (1 - (goal.current_co2 / goal.target_co2))))
                progresses.append(pct)
        return sum(progresses) / len(progresses) if progresses else 0.0

    @api.model
    def _compute_social_score(self, department):
        """Based on CSR participation approval rate (models owned by Person B)."""
        Participation = self.env['eco.employee.participation']
        employees = self.env['hr.employee'].search([('department_id', '=', department.id)])
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
        """Policy acknowledgement rate minus severity-weighted open compliance issues."""
        Ack = self.env['eco.policy.acknowledgement']
        Issue = self.env['eco.compliance.issue']

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
        """Entry point called by ir.cron and can be called manually (e.g. button/API)."""
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
        """Scheduled job (registered in data/ir_cron_data.xml) - recomputes every department."""
        departments = self.env['eco.department'].search([])
        for dept in departments:
            self.recompute_department_score(dept)

    @api.model
    def get_overall_esg_score(self):
        """Weighted average of all departments' latest total_score - for dashboard/reports."""
        departments = self.env['eco.department'].search([])
        scores = []
        for dept in departments:
            latest = self.search(
                [('department_id', '=', dept.id)], order='period_date desc', limit=1
            )
            if latest:
                scores.append(latest.total_score)
        return sum(scores) / len(scores) if scores else 0.0