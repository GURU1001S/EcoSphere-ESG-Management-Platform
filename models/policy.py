from odoo import fields, models


class EcoPolicy(models.Model):
    _name = 'eco.policy'
    _description = 'ESG Policy'

    name = fields.Char(required=True)
    policy_type = fields.Selection([
        ('environmental', 'Environmental'),
        ('social', 'Social'),
        ('governance', 'Governance'),
    ], default='environmental')
    content = fields.Text()
