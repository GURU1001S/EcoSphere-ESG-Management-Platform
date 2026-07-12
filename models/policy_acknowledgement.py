from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PolicyAcknowledgement(models.Model):
    _name = 'esg.policy.acknowledgement'
    _description = 'Employee Policy Acknowledgement'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'policy_id'

    policy_id = fields.Many2one('esg.policy', required=True, ondelete='cascade', tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    department_id = fields.Many2one(
        related='employee_id.esg_department_id', store=True, string='Department'
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('overdue', 'Overdue'),
    ], default='pending', required=True, tracking=True)
    acknowledged_date = fields.Datetime(readonly=True)
    reminder_sent_count = fields.Integer(default=0, readonly=True)
    due_date = fields.Date(help="Deadline for acknowledgement; used for reminder/overdue logic")

    _sql_constraints = [
        ('policy_employee_unique', 'unique(policy_id, employee_id)',
         'An employee can only have one acknowledgement record per policy.')
    ]

    def action_acknowledge(self):
        for rec in self:
            if rec.state == 'acknowledged':
                raise ValidationError("This policy has already been acknowledged.")
            rec.write({
                'state': 'acknowledged',
                'acknowledged_date': fields.Datetime.now(),
            })
            rec._notify_acknowledgement()

    def _notify_acknowledgement(self):
        for rec in self:
            rec.policy_id.message_post(
                body=f"{rec.employee_id.name} acknowledged this policy on {rec.acknowledged_date}.",
                subtype_xmlid='mail.mt_note',
            )

    def action_send_reminder(self):
        for rec in self.filtered(lambda r: r.state in ('pending', 'overdue')):
            if rec.employee_id.user_id:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f"Acknowledge Policy: {rec.policy_id.name}",
                    user_id=rec.employee_id.user_id.id,
                )
            rec.reminder_sent_count += 1

    @api.model
    def _cron_flag_overdue(self):
        if self.env['ir.config_parameter'].sudo().get_param('ecosphere.policy_reminders') != 'True':
            return
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'pending'),
            ('due_date', '!=', False),
            ('due_date', '<', today),
        ])
        overdue.write({'state': 'overdue'})
        overdue.action_send_reminder()
