from odoo import models, fields, api

class CarbonTransaction(models.Model):
    _name = "carbon.transaction"
    _description = "Carbon Transaction"
    
    # PREMIUM FEATURE: This adds a "Chatter" history log to track changes!
    _inherit = ['mail.thread'] 
    _order = 'date desc'

    # PREMIUM FEATURE: Auto-generates a transaction number instead of just "New"
    name = fields.Char(string="Reference", default='New', copy=False, tracking=True)
    
    department_id = fields.Many2one("esg.department", string="Department", required=True, tracking=True)
    emission_factor_id = fields.Many2one("esg.emission.factor", string="Emission Factor", required=True, tracking=True)
    date = fields.Date(string="Date", default=fields.Date.today, required=True, tracking=True)
    quantity = fields.Float(string="Quantity", required=True, tracking=True)
    
    # We MUST keep this named total_emission so your teammate's UI doesn't break!
    total_emission = fields.Float(string="Total Emission", compute="_compute_emission", store=True, tracking=True)
    
    source_type = fields.Selection([
        ('manual', 'Manual'),
        ('purchase', 'Purchase Order'),
        ('manufacturing', 'Manufacturing'),
        ('expense', 'Expense'),
        ('fleet', 'Fleet')
    ], string="Source Type", default='manual', required=True, tracking=True)
    source_ref = fields.Char(string="Source Reference", readonly=True, tracking=True)
    source_model = fields.Char(string="Source Model", readonly=True)
    source_res_id = fields.Integer(string="Source Record ID", readonly=True)

    @api.depends("quantity", "emission_factor_id")
    def _compute_emission(self):
        for rec in self:
            if rec.emission_factor_id:
                rec.total_emission = rec.quantity * rec.emission_factor_id.factor_value
            else:
                rec.total_emission = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('carbon.transaction') or 'New'
        return super().create(vals_list)
