from odoo import models, fields

class EmissionFactor(models.Model):
    _name = "esg.emission.factor"
    _description = "Emission Factor"

    name = fields.Char(string="Name", required=True)
    factor_value = fields.Float(string="Factor Value", required=True)
    unit_of_measure = fields.Char(string="Unit of Measure")