import streamlit as st
import json
import os
import yaml

class StreamlitCloudService:
    def __init__(self):
        """Inicializa o serviço para deploy no Streamlit Community Cloud"""
        pass

    def get_user_credentials(self):
        """Obtém credenciais de usuário dos secrets do Streamlit ou arquivo local"""
        try:
            # Tenta primeiro os secrets do Streamlit (produção)
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'user_credentials'):
                return st.secrets['user_credentials']

            # Fallback para arquivo local (desenvolvimento)
            if os.path.exists('config.yaml'):
                with open('config.yaml', 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file)

            return None

        except Exception as e:
            # Se secrets não existirem, tenta arquivo local sem mostrar erro
            if os.path.exists('config.yaml'):
                try:
                    with open('config.yaml', 'r', encoding='utf-8') as file:
                        return yaml.safe_load(file)
                except Exception as file_error:
                    st.error(f"Erro ao carregar config.yaml: {file_error}")
            else:
                st.error(f"Erro ao carregar credenciais de usuário: {e}")
            return None

    def get_google_sheets_credentials(self):
        """Obtém credenciais do Google Sheets dos secrets do Streamlit ou arquivo local"""
        try:
            # Tenta primeiro os secrets do Streamlit (produção)
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'google_sheets_credentials'):
                # Converte para dict se for um objeto secrets
                creds = dict(st.secrets['google_sheets_credentials'])
                return creds

            # Fallback para arquivo local (desenvolvimento)
            if os.path.exists('credentials.json'):
                with open('credentials.json', 'r', encoding='utf-8') as file:
                    return json.load(file)

            return None

        except Exception as e:
            # Se secrets não existirem, tenta arquivo local sem mostrar erro
            if os.path.exists('credentials.json'):
                try:
                    with open('credentials.json', 'r', encoding='utf-8') as file:
                        return json.load(file)
                except Exception as file_error:
                    st.error(f"Erro ao carregar credentials.json: {file_error}")
            else:
                st.error(f"Erro ao carregar credenciais do Google Sheets: {e}")
            return None

    def get_config_value(self, key, default=None):
        """Obtém valor de configuração dos secrets do Streamlit ou retorna valor padrão"""
        try:
            # Tenta primeiro os secrets do Streamlit
            if hasattr(st, 'secrets') and hasattr(st.secrets, key):
                return st.secrets[key]

            # Se nenhum padrão fornecido e chave não encontrada, mostra erro
            if default is None:
                st.error(f"Configuração obrigatória '{key}' não encontrada nos secrets ou arquivos locais.")
                return None

            # Retorna valor padrão
            return default

        except Exception as e:
            if default is None:
                st.error(f"Erro ao carregar configuração obrigatória '{key}': {e}")
                return None
            else:
                st.warning(f"Configuração '{key}' não encontrada, usando valor padrão")
                return default

    def get_sheet_url(self):
        """Obtém URL da planilha do Google dos secrets do Streamlit ou arquivo config.yaml local"""
        try:
            # Tenta primeiro os secrets do Streamlit (produção)
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'sheet_url'):
                return st.secrets['sheet_url']

            # Fallback para arquivo local config.yaml (desenvolvimento)
            if os.path.exists('config.yaml'):
                try:
                    with open('config.yaml', 'r', encoding='utf-8') as file:
                        config = yaml.safe_load(file)
                        if config and 'sheet_url' in config:
                            return config['sheet_url']
                except Exception as file_error:
                    st.error(f"Erro ao carregar sheet_url do config.yaml: {file_error}")

            st.error("URL da planilha não encontrada. Configure 'sheet_url' nos secrets do Streamlit Cloud ou no arquivo config.yaml local.")
            return None

        except Exception as e:
            st.error(f"Erro ao carregar URL da planilha: {e}")
            return None

    def validate_secrets(self):
        """Valida se todos os secrets obrigatórios estão configurados (apenas no Streamlit Cloud)"""
        # Se não estamos no Streamlit Cloud, pula a validação
        # Detecta ambiente local verificando se arquivos de configuração existem
        if os.path.exists('config.yaml') or os.path.exists('credentials.json'):
            return True

        # Se chegou aqui, provavelmente está no Streamlit Cloud
        if not hasattr(st, 'secrets'):
            st.error("Ambiente Streamlit Cloud detectado, mas secrets não estão disponíveis.")
            return False

        required_secrets = [
            'user_credentials',
            'google_sheets_credentials',
            'sheet_url'
        ]

        missing_secrets = []

        for secret in required_secrets:
            try:
                if not hasattr(st.secrets, secret):
                    missing_secrets.append(secret)
            except Exception:
                missing_secrets.append(secret)

        if missing_secrets:
            st.error(f"Secrets obrigatórios não configurados: {', '.join(missing_secrets)}")
            st.info("Configure estes secrets no Streamlit Community Cloud em Settings → Secrets")
            return False

        return True
