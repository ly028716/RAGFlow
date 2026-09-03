from app.models.agent_execution import AgentExecution, ExecutionStatus


def test_agent_execution_status_maps_database_values_to_enum_values():
    status_type = AgentExecution.__table__.c.status.type

    assert status_type.enums == [status.value for status in ExecutionStatus]
