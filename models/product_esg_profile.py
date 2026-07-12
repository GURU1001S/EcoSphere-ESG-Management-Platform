from odoo import fields, models


class ProductESGProfile(models.Model):
    _inherit = 'product.template'

    esg_score = fields.Float(string='ESG Score', digits='Account')
    carbon_footprint = fields.Float(string='Carbon Footprint', digits='Account')
    sustainability_label = fields.Char()
