from odoo import fields, models


class EcoPolicyAcknowledgement(models.Model):
    _name = 'eco.policy.acknowledgement'
    _description = 'Policy Acknowledgement'

    employee_id = fields.Many2one('hr.employee', required=True)
    policy_id = fields.Many2one('eco.policy', required=True)
    acknowledged_on = fields.Date(default=fields.Date.context_today)
