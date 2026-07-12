from odoo import api, fields, models


class ProductESGProfile(models.Model):
    _inherit = 'product.template'

    esg_score = fields.Float(string='ESG Score', digits='Account')
    carbon_footprint = fields.Float(string='Carbon Footprint', digits='Account')
    sustainability_label = fields.Char()
    emission_factor_id = fields.Many2one('esg.emission.factor', string='Emission Factor')
    emission_factor_estimated = fields.Boolean(string='Emission Factor Estimated', readonly=True)
    emission_factor_note = fields.Text(string='Emission Factor Note', readonly=True)

    def action_estimate_emission_factor(self):
        for product in self:
            product._estimate_emission_factor()
        return True

    def _estimate_emission_factor(self):
        self.ensure_one()
        if self.emission_factor_id:
            return self.emission_factor_id

        name = (self.name or '').lower()
        factor_value = 1.0
        unit = self.uom_id.name if self.uom_id else 'unit'

        if any(token in name for token in ['diesel', 'fuel', 'petrol', 'gasoline']):
            factor_value = 2.68
            unit = 'litre'
        elif any(token in name for token in ['electric', 'power', 'energy', 'kwh']):
            factor_value = 0.82
            unit = 'kWh'
        elif any(token in name for token in ['flight', 'air', 'travel']):
            factor_value = 0.25
            unit = 'km'
        elif any(token in name for token in ['paper', 'print']):
            factor_value = 1.30
            unit = 'kg'
        elif self.carbon_footprint:
            factor_value = self.carbon_footprint

        factor = self.env['esg.emission.factor'].create({
            'name': f'Estimated - {self.name}',
            'factor_value': factor_value,
            'unit_of_measure': unit,
        })
        self.write({
            'emission_factor_id': factor.id,
            'emission_factor_estimated': True,
            'emission_factor_note': 'Estimated locally from product keywords or product carbon footprint.',
        })
        return factor


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        result = super().button_confirm()
        if self.env['ir.config_parameter'].sudo().get_param('ecosphere.auto_emission') == 'True':
            for order in self:
                order._create_ecosphere_carbon_transactions()
        return result

    def _create_ecosphere_carbon_transactions(self):
        Carbon = self.env['carbon.transaction']
        for order in self:
            department = self._get_ecosphere_department()
            if not department:
                continue
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                product = line.product_id.product_tmpl_id
                factor = product.emission_factor_id or product._estimate_emission_factor()
                quantity = line.product_qty or 0.0
                if not factor or quantity <= 0:
                    continue
                Carbon.create({
                    'department_id': department.id,
                    'emission_factor_id': factor.id,
                    'date': order.date_order.date() if order.date_order else fields.Date.today(),
                    'quantity': quantity,
                    'source_type': 'purchase',
                    'source_ref': order.name,
                    'source_model': order._name,
                    'source_res_id': order.id,
                })

    def _get_ecosphere_department(self):
        employee = self.env.user.employee_id
        department = employee.esg_department_id if employee else False
        if not department:
            department = self.env['esg.department'].search([], limit=1)
        return department


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def button_mark_done(self):
        result = super().button_mark_done()
        if self.env['ir.config_parameter'].sudo().get_param('ecosphere.auto_emission') == 'True':
            for production in self:
                production._create_ecosphere_carbon_transaction()
        return result

    def _create_ecosphere_carbon_transaction(self):
        Carbon = self.env['carbon.transaction']
        for production in self:
            product = production.product_id.product_tmpl_id
            factor = product.emission_factor_id or product._estimate_emission_factor()
            department = self.env.user.employee_id.esg_department_id or self.env['esg.department'].search([], limit=1)
            quantity = production.product_qty or 0.0
            if factor and department and quantity > 0:
                Carbon.create({
                    'department_id': department.id,
                    'emission_factor_id': factor.id,
                    'date': fields.Date.today(),
                    'quantity': quantity,
                    'source_type': 'manufacturing',
                    'source_ref': production.name,
                    'source_model': production._name,
                    'source_res_id': production.id,
                })


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def action_submit_expenses(self):
        result = super().action_submit_expenses()
        if self.env['ir.config_parameter'].sudo().get_param('ecosphere.auto_emission') == 'True':
            self._create_ecosphere_carbon_transactions()
        return result

    def _create_ecosphere_carbon_transactions(self):
        Carbon = self.env['carbon.transaction']
        fallback_factor = self.env['esg.emission.factor'].search([('name', 'ilike', 'travel')], limit=1)
        for expense in self:
            department = expense.employee_id.esg_department_id or self.env['esg.department'].search([], limit=1)
            quantity = expense.quantity or 1.0
            factor = fallback_factor
            if expense.product_id:
                product = expense.product_id.product_tmpl_id
                factor = product.emission_factor_id or product._estimate_emission_factor()
            if factor and department:
                Carbon.create({
                    'department_id': department.id,
                    'emission_factor_id': factor.id,
                    'date': expense.date or fields.Date.today(),
                    'quantity': quantity,
                    'source_type': 'expense',
                    'source_ref': expense.name,
                    'source_model': expense._name,
                    'source_res_id': expense.id,
                })


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env['ir.config_parameter'].sudo().get_param('ecosphere.auto_emission') == 'True':
            records._create_ecosphere_carbon_transactions()
        return records

    def _create_ecosphere_carbon_transactions(self):
        Carbon = self.env['carbon.transaction']
        fuel_factor = self.env['esg.emission.factor'].search([
            '|', ('name', 'ilike', 'fuel'), ('name', 'ilike', 'diesel')
        ], limit=1)
        if not fuel_factor:
            fuel_factor = self.env['esg.emission.factor'].create({
                'name': 'Estimated - Fleet Fuel',
                'factor_value': 2.68,
                'unit_of_measure': 'litre',
            })
        department = self.env.user.employee_id.esg_department_id or self.env['esg.department'].search([], limit=1)
        for service in self:
            quantity = 1.0
            if 'amount' in service._fields and service.amount:
                quantity = service.amount
            elif 'odometer' in service._fields and service.odometer:
                quantity = service.odometer
            if department:
                Carbon.create({
                    'department_id': department.id,
                    'emission_factor_id': fuel_factor.id,
                    'date': service.date or fields.Date.today(),
                    'quantity': quantity,
                    'source_type': 'fleet',
                    'source_ref': service.display_name,
                    'source_model': service._name,
                    'source_res_id': service.id,
                })
