from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    env_goal_default_year = fields.Integer(string='Default Goal Year')
    score_threshold = fields.Float(string='Department Score Threshold', default=75.0)
