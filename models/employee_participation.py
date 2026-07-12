from odoo import fields, models


class EcoEmployeeParticipation(models.Model):
    _name = 'eco.employee.participation'
    _description = 'Employee Participation'

    employee_id = fields.Many2one('hr.employee', required=True)
    activity_id = fields.Many2one('eco.csr.activity', required=True)
    status = fields.Selection([
        ('registered', 'Registered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='registered')
