from odoo import fields, models


class EcoRewardRedemption(models.Model):
    _name = 'esg.reward.redemption'
    _description = 'Reward Redemption'

    employee_id = fields.Many2one('hr.employee', required=True)
    reward_id = fields.Many2one('esg.reward', required=True)
    redeemed_on = fields.Date(default=fields.Date.context_today)
    points_spent = fields.Integer(required=True)
