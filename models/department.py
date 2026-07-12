from odoo import fields, models


class EcoDepartment(models.Model):
    _name = 'eco.department'
    _description = 'EcoSphere Department'

    name = fields.Char(required=True)
    manager_id = fields.Many2one('hr.employee', string='Manager')
    category_ids = fields.Many2many('eco.category', string='Categories')
    score = fields.Float(string='ESG Score', digits='Account')
