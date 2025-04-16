from clickhouse_backend.backend.base import (
    DatabaseWrapper as BaseDatabaseWrapper,
    DatabaseSchemaEditor as BaseDatabaseSchemaEditor,
)

class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    pass

class DatabaseWrapper(BaseDatabaseWrapper):
    SchemaEditorClass = DatabaseSchemaEditor