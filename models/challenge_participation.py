from odoo import fields, models


class EcoChallengeParticipation(models.Model):
    _name = 'eco.challenge.participation'
    _description = 'Challenge Participation'

    employee_id = fields.Many2one('hr.employee', required=True)
    challenge_id = fields.Many2one('eco.challenge', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ], default='pending')
