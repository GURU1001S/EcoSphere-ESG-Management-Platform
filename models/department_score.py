from odoo import fields, models


class EcoDepartmentScore(models.Model):
    _name = 'eco.department.score'
    _description = 'Department Score'

    department_id = fields.Many2one('eco.department', required=True)
    score = fields.Float(digits='Account')
    computed_score = fields.Float(digits='Account')
