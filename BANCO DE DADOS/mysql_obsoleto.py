#!/usr/bin/env python3
import pymysql
import pymysql.constants.CLIENT as CLIENT
import argparse
import sys

class MySQLAntigo:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        """Estabelece conexão com o MySQL antigo"""
        try:
            config = {
                'host': self.host,
                'port': self.port,
                'user': self.user,
                'password': self.password,
                'database': self.database,
                'charset': 'latin1',
                'use_unicode': False,
                'client_flag': CLIENT.MULTI_STATEMENTS,
                'connect_timeout': 10
            }

            self.connection = pymysql.connect(**config)
            return True
        except pymysql.Error as e:
            print(f"❌ Erro de conexão: {e}")
            return False

    def close(self):
        """Fecha a conexão"""
        if self.connection:
            self.connection.close()

    def decode_bytes(self, value):
        """Decodifica bytes para string se necessário"""
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return value

    def show_tables(self):
        """Lista todas as tabelas do banco"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            if tables:
                print(f"\n📋 Tabelas no banco '{self.database}':")
                print("-" * 40)
                for i, table in enumerate(tables, 1):
                    table_name = self.decode_bytes(table[0])
                    print(f"  {i}. {table_name}")
                print(f"\n✅ Total: {len(tables)} tabela(s)")
            else:
                print(f"\n⚠️ Nenhuma tabela encontrada no banco '{self.database}'")

            cursor.close()
        except pymysql.Error as e:
            print(f"❌ Erro ao listar tabelas: {e}")

    def show_columns(self, table):
        """Mostra as colunas de uma tabela específica"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"DESCRIBE `{table}`")
            columns = cursor.fetchall()

            if columns:
                print(f"\n📊 Estrutura da tabela '{table}':")
                print("-" * 70)
                print(f"{'Campo':<20} {'Tipo':<25} {'Nulo':<8} {'Chave':<8} {'Padrão':<15}")
                print("-" * 70)
                for col in columns:
                    field = self.decode_bytes(col[0])
                    col_type = self.decode_bytes(col[1])
                    null = self.decode_bytes(col[2])
                    key = self.decode_bytes(col[3]) if col[3] else ''
                    default = self.decode_bytes(col[4]) if col[4] else 'NULL'

                    print(f"{field:<20} {col_type:<25} {null:<8} {key:<8} {default:<15}")
            else:
                print(f"⚠️ Tabela '{table}' não encontrada ou não tem colunas")

            cursor.close()
        except pymysql.Error as e:
            print(f"❌ Erro ao mostrar colunas: {e}")

    def dump_table(self, table, limit=None):
        """Mostra todos os registros de uma tabela"""
        try:
            cursor = self.connection.cursor()

            # Primeiro, pega as colunas
            cursor.execute(f"DESCRIBE `{table}`")
            columns = [self.decode_bytes(col[0]) for col in cursor.fetchall()]

            if not columns:
                print(f"⚠️ Tabela '{table}' não encontrada")
                return

            # Consulta os dados
            query = f"SELECT * FROM `{table}`"
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            rows = cursor.fetchall()

            if rows:
                print(f"\n📝 Dados da tabela '{table}':")
                print("-" * 80)

                # Mostra cabeçalho
                header = " | ".join(columns)
                print(f"{header}")
                print("-" * min(80, len(header)))

                # Mostra registros
                for i, row in enumerate(rows, 1):
                    # Decodifica cada campo
                    decoded_row = [self.decode_bytes(val) for val in row]
                    print(f"{i}. {' | '.join(str(val) for val in decoded_row)}")

                print(f"\n✅ Total: {len(rows)} registro(s)")
            else:
                print(f"\n📭 Tabela '{table}' está vazia")

            cursor.close()
        except pymysql.Error as e:
            print(f"❌ Erro ao fazer dump da tabela: {e}")

    def execute_query(self, query):
        """Executa uma consulta SQL personalizada"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)

            # Se for SELECT, mostra resultados
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                if rows:
                    # Pega nomes das colunas
                    columns = [self.decode_bytes(col[0]) for col in cursor.description]
                    print("\n🔍 Resultado da consulta:")
                    print("-" * 60)
                    print(" | ".join(columns))
                    print("-" * 60)

                    for row in rows:
                        decoded_row = [self.decode_bytes(val) for val in row]
                        print(" | ".join(str(val) for val in decoded_row))

                    print(f"\n✅ {len(rows)} linha(s) retornada(s)")
                else:
                    print("✅ Consulta executada com sucesso (0 linhas retornadas)")
            else:
                # Para INSERT, UPDATE, DELETE
                self.connection.commit()
                print(f"✅ Consulta executada com sucesso. {cursor.rowcount} linha(s) afetadas.")

            cursor.close()
        except pymysql.Error as e:
            print(f"❌ Erro na consulta: {e}")

def show_help():
    """Mostra ajuda detalhada"""
    help_text = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     MYSQL ANTIGO CLIENT - Manual de Uso                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📌 SINTAXE:
    python3 mysql_antigo_connect.py <HOST> <PORTA> <USUARIO> <SENHA> -D <BANCO> [OPÇÕES]

📋 ARGUMENTOS OBRIGATÓRIOS:
    HOST        Endereço do servidor MySQL (ex: 192.168.93.112)
    PORTA       Porta do MySQL (normalmente 3306)
    USUARIO     Nome do usuário para autenticação
    SENHA       Senha do usuário
    -D BANCO    Nome do banco de dados

🔧 OPÇÕES DISPONÍVEIS:
    --tables                    Lista todas as tabelas do banco
    -T <tabela>                 Especifica uma tabela para operações
    --columns                   Mostra as colunas da tabela (requer -T)
    --dump                      Mostra todos os registros da tabela (requer -T)
    --query "<SQL>"             Executa uma consulta SQL personalizada
    --limit <numero>            Limita o número de registros no dump

📖 EXEMPLOS DE USO:

    1️⃣  Listar todas as tabelas:
        python3 mysql_antigo_connect.py 192.168.93.112 3306 ctp senha123 -D exam --tables

    2️⃣  Ver estrutura de uma tabela:
        python3 mysql_antigo_connect.py 192.168.93.112 3306 ctp senha123 -D exam -T users --columns

    3️⃣  Ver todos os dados de uma tabela:
        python3 mysql_antigo_connect.py 192.168.93.112 3306 ctp senha123 -D exam -T users --dump

    4️⃣  Ver dados com limite:
        python3 mysql_antigo_connect.py 192.168.93.112 3306 ctp senha123 -D exam -T users --dump --limit 10

    5️⃣  Executar consulta personalizada:
        python3 mysql_antigo_connect.py 192.168.93.112 3306 ctp senha123 -D exam --query "SELECT * FROM users WHERE id=1"

    6️⃣  Múltiplas operações:
        python3 mysql_antigo_connect.py 192.168.93.112 3306 ctp senha123 -D exam --tables -T users --columns --dump

💡 DICAS:
    • Use --help para mostrar esta ajuda
    • As aspas na consulta SQL são obrigatórias quando há espaços
    • O script suporta MySQL 4.x e 5.x com autenticação antiga

⚠️  ATENÇÃO:
    • Este cliente é específico para servidores MySQL antigos (versão < 5.7)
    • Conexões não usam SSL por compatibilidade
    """
    print(help_text)

def main():
    # Verificar se não há argumentos ou se pediu help
    if len(sys.argv) == 1 or '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        sys.exit(0)

    # Verificar número mínimo de argumentos (host, porta, user, pass, -D, database)
    if len(sys.argv) < 7:
        print("\n❌ ERRO: Argumentos insuficientes!\n")
        print("💡 Uso correto: python3 mysql_antigo_connect.py <HOST> <PORTA> <USUARIO> <SENHA> -D <BANCO> [OPÇÕES]")
        print("📖 Para mais detalhes, use: python3 mysql_antigo_connect.py --help\n")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description='Cliente MySQL para versões antigas (MySQL 4.x/5.x)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False  # Desabilitamos o help padrão para usar o nosso
    )

    # Argumentos posicionais
    parser.add_argument('host', help='Host do MySQL')
    parser.add_argument('port', type=int, help='Porta do MySQL')
    parser.add_argument('user', help='Usuário do MySQL')
    parser.add_argument('password', help='Senha do MySQL')

    # Argumentos opcionais
    parser.add_argument('-D', '--database', required=True, help='Banco de dados')
    parser.add_argument('--tables', action='store_true', help='Listar todas as tabelas')
    parser.add_argument('-T', '--table', help='Nome da tabela para operações')
    parser.add_argument('--columns', action='store_true', help='Mostrar colunas da tabela')
    parser.add_argument('--dump', action='store_true', help='Fazer dump de todos os registros')
    parser.add_argument('--query', help='Executar consulta SQL personalizada')
    parser.add_argument('--limit', type=int, help='Limitar número de registros no dump')

    try:
        args = parser.parse_args()
    except SystemExit:
        # Se o parse falhar, mostra nosso help personalizado
        show_help()
        sys.exit(1)

    # Validação dos argumentos
    if args.table and not (args.columns or args.dump):
        print("\n⚠️ ERRO: Com a opção -T, você precisa usar --columns ou --dump")
        print("💡 Exemplo: -T users --columns")
        print("💡 Exemplo: -T users --dump\n")
        sys.exit(1)

    if args.columns and not args.table:
        print("\n⚠️ ERRO: Opção --columns requer -T para especificar a tabela")
        print("💡 Exemplo: -T users --columns\n")
        sys.exit(1)

    if args.dump and not args.table:
        print("\n⚠️ ERRO: Opção --dump requer -T para especificar a tabela")
        print("💡 Exemplo: -T users --dump\n")
        sys.exit(1)

    if args.limit and not args.dump:
        print("\n⚠️ ERRO: Opção --limit só pode ser usada com --dump")
        print("💡 Exemplo: -T users --dump --limit 10\n")
        sys.exit(1)

    # Cria instância e conecta
    cliente = MySQLAntigo(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )

    print(f"\n🔌 Conectando a {args.host}:{args.port}...")
    if not cliente.connect():
        sys.exit(1)

    print(f"✅ Conectado com sucesso | Banco: {args.database}\n")

    # Executa a ação solicitada
    if args.tables:
        cliente.show_tables()

    if args.table and args.columns:
        cliente.show_columns(args.table)

    if args.table and args.dump:
        cliente.dump_table(args.table, args.limit)

    if args.query:
        cliente.execute_query(args.query)

    cliente.close()
    print("\n🔒 Conexão encerrada\n")

if __name__ == "__main__":
    main()
