from odoo import fields, models


class EcoCarbonTransaction(models.Model):
    _name = 'eco.carbon.transaction'
    _description = 'Carbon Transaction'

    name = fields.Char(required=True)
    department_id = fields.Many2one('eco.department')
    amount = fields.Float(required=True)
    transaction_date = fields.Date(default=fields.Date.context_today)
    note = fields.Text()
