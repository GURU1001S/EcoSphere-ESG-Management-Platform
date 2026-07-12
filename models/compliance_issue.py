from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ComplianceIssue(models.Model):
    _name = 'eco.compliance.issue'
    _description = 'Governance Compliance Issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'severity desc, due_date asc'

    name = fields.Char(default='New', copy=False, tracking=True)
    audit_id = fields.Many2one('eco.audit', string='Related Audit', tracking=True)
    department_id = fields.Many2one(
        related='audit_id.department_id', store=True, string='Department', readonly=True
    )
    description = fields.Text(required=True, tracking=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium', required=True, tracking=True)
    owner_id = fields.Many2one('hr.employee', required=True, string='Owner', tracking=True)
    due_date = fields.Date(required=True, tracking=True)
    status = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ], default='open', required=True, tracking=True)
    resolution_notes = fields.Text()
    is_overdue = fields.Boolean(compute='_compute_is_overdue', store=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Compliance issue reference must be unique.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('eco.compliance.issue') or 'New'
        records = super().create(vals_list)
        records._notify_new_issue()
        return records

    @api.depends('due_date', 'status')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_overdue = bool(
                rec.due_date and rec.due_date < today and rec.status != 'resolved'
            )

    def _notify_new_issue(self):
        """Notification System requirement: alert on new compliance issue raised."""
        for rec in self:
            if rec.owner_id.user_id:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f"New Compliance Issue Assigned: {rec.name}",
                    note=rec.description,
                    user_id=rec.owner_id.user_id.id,
                    date_deadline=rec.due_date,
                )

    def action_start_progress(self):
        self.write({'status': 'in_progress'})

    def action_resolve(self):
        for rec in self:
            if not rec.resolution_notes:
                raise ValidationError("Resolution notes are required before resolving an issue.")
            rec.write({'status': 'resolved'})

    @api.model
    def _cron_flag_overdue_issues(self):
        """Called by ir.cron to re-notify owners of overdue open/in-progress issues."""
        today = fields.Date.today()
        overdue = self.search([
            ('due_date', '<', today),
            ('status', '!=', 'resolved'),
        ])
        for rec in overdue:
            if rec.owner_id.user_id:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f"OVERDUE Compliance Issue: {rec.name}",
                    user_id=rec.owner_id.user_id.id,
                )