from odoo import models, fields

class Category(models.Model):
    _name = "esg.category"
    _description = "ESG Category"

    name = fields.Char(string="Name", required=True)
    
    type = fields.Selection([
        ('csr', 'CSR Activity'),
        ('challenge', 'Challenge')
    ], string="Type", required=True)
    
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string="Status", default='active')