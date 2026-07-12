from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EsgAudit(models.Model):
    _name = 'esg.audit'
    _description = 'Governance Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(default='New', copy=False, tracking=True)
    title = fields.Char(required=True, tracking=True)
    department_id = fields.Many2one('esg.department', required=True, tracking=True)
    auditor_id = fields.Many2one('hr.employee', required=True, string='Auditor', tracking=True)
    date = fields.Date(default=fields.Date.today, required=True, tracking=True)
    audit_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
        ('regulatory', 'Regulatory'),
    ], default='internal', required=True)
    scope = fields.Text(help="What areas/processes this audit covers")
    findings = fields.Text()
    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('under_review', 'Under Review'),
        ('completed', 'Completed'),
    ], default='planned', required=True, tracking=True)

    compliance_issue_ids = fields.One2many('esg.compliance.issue', 'audit_id', string='Compliance Issues')
    issue_count = fields.Integer(compute='_compute_issue_stats')
    open_issue_count = fields.Integer(compute='_compute_issue_stats')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Audit reference must be unique.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('esg.audit') or 'New'
        return super().create(vals_list)

    @api.depends('compliance_issue_ids.status')
    def _compute_issue_stats(self):
        for rec in self:
            rec.issue_count = len(rec.compliance_issue_ids)
            rec.open_issue_count = len(
                rec.compliance_issue_ids.filtered(lambda i: i.status == 'open')
            )

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_submit_for_review(self):
        for rec in self:
            if not rec.findings:
                raise ValidationError("Findings must be documented before submitting for review.")
            rec.state = 'under_review'

    def action_complete(self):
        for rec in self:
            if rec.open_issue_count:
                raise ValidationError(
                    "Cannot mark audit as completed while there are still open compliance issues. "
                    "Resolve or reassign them first."
                )
            rec.state = 'completed'