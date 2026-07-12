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

    env_score = fields.Float(string="Environmental Score")
    social_score = fields.Float(string="Social Score")
    gov_score = fields.Float(string="Governance Score")
    total_score = fields.Float(string="Total Score", compute="_compute_total_score", store=True)

    @api.depends("env_score", "social_score", "gov_score")
    def _compute_total_score(self):
        for rec in self:
            rec.total_score = (rec.env_score * 0.4) + (rec.social_score * 0.3) + (rec.gov_score * 0.3)