from odoo import fields, models


class EcoEnvironmentalGoal(models.Model):
    _name = 'eco.environmental.goal'
    _description = 'Environmental Goal'

    name = fields.Char(required=True)
    target_year = fields.Integer()
    achieved = fields.Boolean(default=False)
    description = fields.Text()
