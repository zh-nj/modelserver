"""${message}

修订ID: ${up_revision}
修订时间: ${create_date}
${f"下级修订: {down_revision}" if down_revision else ""}
${f"分支标签: {branch_labels}" if branch_labels else ""}
${f"依赖修订: {depends_on}" if depends_on else ""}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# 修订标识符，由Alembic使用
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """升级数据库结构"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """降级数据库结构"""
    ${downgrades if downgrades else "pass"}