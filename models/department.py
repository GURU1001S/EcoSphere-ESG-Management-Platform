from odoo import models, fields, api

class Department(models.Model):
    _name = "esg.department"
    _description = "ESG Department"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    head_id = fields.Many2one("hr.employee", string="Head") 
    parent_id = fields.Many2one("esg.department", string="Parent Department")
    employee_count = fields.Integer(string="Employee Count")
    
    status = fields.Selection([
        ('active', 'Active'), 
        ('inactive', 'Inactive')
    ], string="Status", default='active')

