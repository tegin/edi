# Copyright 2022 Creu Blanca - Alba Riera

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):

    if openupgrade.column_exists(env.cr, "account_move", "disable_edi_auto"):
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE account_move
                ADD edi_auto_disabled boolean;
            UPDATE account_move
                SET edi_auto_disabled = disable_edi_auto;
            ALTER TABLE account_move
                DROP COLUMN disable_edi_auto;
            """,
        )
