from odoo import fields, models


class EcoEmissionFactor(models.Model):
    _name = 'eco.emission.factor'
    _description = 'Emission Factor'

    name = fields.Char(required=True)
    source = fields.Char()
    factor = fields.Float(required=True)
    unit = fields.Char(default='kg CO2e')
