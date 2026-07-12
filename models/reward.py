from odoo import fields, models


class EcoReward(models.Model):
    _name = 'eco.reward'
    _description = 'EcoSphere Reward'

    name = fields.Char(required=True)
    points_required = fields.Integer()
    expiry_date = fields.Date()
