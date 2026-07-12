from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrEmployeeEsgInherit(models.Model):
    """Bridge field: links native hr.employee to the custom esg.department model,
    since esg.department is kept separate from hr.department by team decision."""
    _inherit = 'hr.employee'

    esg_department_id = fields.Many2one('esg.department', string='ESG Department')


class EsgPolicy(models.Model):
    _name = 'esg.policy'
    _description = 'ESG Governance Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True, copy=False)
    category = fields.Selection([
        ('environmental', 'Environmental'),
        ('social', 'Social'),
        ('governance', 'Governance'),
        ('general', 'General'),
    ], required=True, default='general', tracking=True)
    description = fields.Text()
    document = fields.Binary(string='Policy Document', attachment=True)
    document_filename = fields.Char()
    department_ids = fields.Many2many(
        'esg.department', string='Applicable Departments',
        help="Leave empty to apply to all departments"
    )
    version = fields.Char(default='1.0', tracking=True)
    effective_date = fields.Date(required=True, default=fields.Date.today, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], default='draft', required=True, tracking=True)
    active = fields.Boolean(default=True)

    acknowledgement_ids = fields.One2many(
        'esg.policy.acknowledgement', 'policy_id', string='Acknowledgements'
    )
    acknowledgement_count = fields.Integer(compute='_compute_acknowledgement_stats')
    acknowledgement_rate = fields.Float(
        compute='_compute_acknowledgement_stats', string='Acknowledgement Rate (%)',
        help="Percentage of required employees who have acknowledged this policy"
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Policy code must be unique.')
    ]

    @api.depends('acknowledgement_ids.state')
    def _compute_acknowledgement_stats(self):
        for rec in self:
            total = len(rec.acknowledgement_ids)
            acked = len(rec.acknowledgement_ids.filtered(lambda a: a.state == 'acknowledged'))
            rec.acknowledgement_count = acked
            rec.acknowledgement_rate = (acked / total * 100.0) if total else 0.0

    @api.constrains('effective_date')
    def _check_effective_date(self):
        for rec in self:
            if rec.state == 'draft':
                continue
            if not rec.effective_date:
                raise ValidationError("Effective date is required to activate a policy.")

    def action_activate(self):
        for rec in self:
            if not rec.document:
                raise ValidationError("Cannot activate a policy without an attached document.")
            rec.state = 'active'
            rec._generate_acknowledgement_requests()

    def action_archive_policy(self):
        self.write({'state': 'archived'})

    def _generate_acknowledgement_requests(self):
        """Create pending acknowledgement records for all relevant employees,
        looked up via the esg_department_id bridge field on hr.employee."""
        Employee = self.env['hr.employee']
        for rec in self:
            domain = []
            if rec.department_ids:
                domain = [('esg_department_id', 'in', rec.department_ids.ids)]
            employees = Employee.search(domain)
            existing_emp_ids = rec.acknowledgement_ids.mapped('employee_id').ids
            to_create = employees.filtered(lambda e: e.id not in existing_emp_ids)
            for emp in to_create:
                self.env['esg.policy.acknowledgement'].create({
                    'policy_id': rec.id,
                    'employee_id': emp.id,
                    'state': 'pending',
                })