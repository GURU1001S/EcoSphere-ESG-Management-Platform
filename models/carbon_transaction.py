from odoo import models, fields, api

class CarbonTransaction(models.Model):
    _name = 'eco.carbon.transaction'
    _description = 'Carbon Transaction'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(default='New', copy=False)
    department_id = fields.Many2one('eco.department', required=True, tracking=True)
    emission_factor_id = fields.Many2one('eco.emission.factor', required=True)
    date = fields.Date(default=fields.Date.today, required=True)
    quantity = fields.Float(required=True)
    co2_emitted = fields.Float(compute='_compute_co2', store=True, string='CO2e (kg)')
    source_type = fields.Selection([
        ('manual', 'Manual'),
        ('purchase', 'Purchase Order'),
        ('manufacturing', 'Manufacturing'),
        ('expense', 'Expense'),
        ('fleet', 'Fleet'),
    ], default='manual', required=True)

    # native integration links
    purchase_line_id = fields.Many2one('purchase.order.line')
    mrp_production_id = fields.Many2one('mrp.production')
    hr_expense_id = fields.Many2one('hr.expense')
    fleet_vehicle_id = fields.Many2one('fleet.vehicle')

    @api.depends('quantity', 'emission_factor_id.factor_value')
    def _compute_co2(self):
        for rec in self:
            rec.co2_emitted = rec.quantity * rec.emission_factor_id.factor_value

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('eco.carbon.transaction') or 'New'
        return super().create(vals_list)
