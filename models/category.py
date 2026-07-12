from odoo import fields, models


class EcoCategory(models.Model):
    _name = 'eco.category'
    _description = 'EcoSphere Category'

    name = fields.Char(required=True)
    description = fields.Text()
