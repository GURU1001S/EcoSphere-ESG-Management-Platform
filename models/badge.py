from odoo import fields, models


class EcoBadge(models.Model):
    _name = 'eco.badge'
    _description = 'EcoSphere Badge'

    name = fields.Char(required=True)
    criteria = fields.Text()
    points = fields.Integer(default=0)
