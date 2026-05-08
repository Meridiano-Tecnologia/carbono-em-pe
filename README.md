# Carbono em Pé

Plataforma de estimativa de estoque de carbono para propriedades rurais brasileiras.

## Stack

- **Frontend:** React + Vite + Tailwind — deploy no Vercel
- **Backend:** FastAPI (Python) — deploy no Railway
- **Banco de dados:** Supabase (PostgreSQL)

## Setup do Supabase

### Grants obrigatórios por tabela

Toda tabela criada no Supabase precisa ter permissões explícitas concedidas ao role `anon` e/ou `authenticated` usado pelo backend. Se uma tabela for **recriada ou migrada**, os grants abaixo devem ser reaplicados no **SQL Editor** do Supabase.

#### Tabela `consentimentos`

```sql
-- Permite que o service role (usado pelo backend via supabase-py) insira registros
GRANT INSERT ON TABLE consentimentos TO service_role;
GRANT SELECT ON TABLE consentimentos TO service_role;

-- Se RLS estiver habilitado, criar policy para o service_role
ALTER TABLE consentimentos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role acesso total" ON consentimentos
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
```

#### Tabela `usuarios`

```sql
GRANT INSERT, SELECT, UPDATE ON TABLE usuarios TO service_role;
```

#### Tabela `analises`

```sql
GRANT INSERT, SELECT, UPDATE ON TABLE analises TO service_role;
```

#### Tabela `pagamentos`

```sql
GRANT INSERT, SELECT, UPDATE ON TABLE pagamentos TO service_role;
```

### Verificar grants ativos

```sql
SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
ORDER BY table_name, grantee;
```

### Verificar policies de RLS

```sql
SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;
```

## Variáveis de ambiente

### Backend (Railway)

| Variável | Descrição |
|---|---|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_KEY` | Chave `service_role` do Supabase |
| `SECRET_KEY` | Chave para assinar tokens JWT |
| `STRIPE_SECRET_KEY` | Chave secreta do Stripe |
| `STRIPE_WEBHOOK_SECRET` | Secret do webhook do Stripe |

### Frontend (Vercel)

| Variável | Descrição |
|---|---|
| `VITE_API_URL` | URL base do backend |
