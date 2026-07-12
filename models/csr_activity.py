from odoo import fields, models


class EcoCSRActivity(models.Model):
    _name = 'eco.csr.activity'
    _description = 'CSR Activity'

    name = fields.Char(required=True)
    description = fields.Text()
    start_date = fields.Date()
    end_date = fields.Date()
    participant_count = fields.Integer()
