-- postgres/init.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Índices para performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_meals_user_id_date ON meals(user_id, date);
CREATE INDEX idx_workouts_user_id_date ON workouts(user_id, date);
CREATE INDEX idx_progress_logs_user_id_date ON progress_logs(user_id, date);