import streamlit as st
import json
import os
import yaml

class StreamlitCloudService:
    def __init__(self):
        """Inicializa o serviço para deploy no Streamlit Community Cloud"""
        pass

    def _convert_secrets_to_dict(self, secrets_obj):
        """Converte objetos secrets do Streamlit em dicionários Python comuns recursivamente"""
        import copy
        
        # Se for None, retorna None
        if secrets_obj is None:
            return None
            
        # Se for um objeto secrets do Streamlit, converte para dict
        if hasattr(secrets_obj, '_data'):
            try:
                # Para objetos secrets do Streamlit, acessa os dados internos
                data = dict(secrets_obj._data)
                # Converte recursivamente todos os valores
                result = {}
                for key, value in data.items():
                    result[key] = self._convert_secrets_to_dict(value)
                return result
            except Exception:
                # Se falhar, tenta converter diretamente para dict
                try:
                    return dict(secrets_obj)
                except Exception:
                    pass
                    
        # Tenta métodos de conversão alternativos para objetos secrets
        elif hasattr(secrets_obj, 'to_dict'):
            try:
                return self._convert_secrets_to_dict(secrets_obj.to_dict())
            except Exception:
                pass
                
        # Se for um dicionário normal, converte recursivamente
        elif isinstance(secrets_obj, dict):
            result = {}
            for key, value in secrets_obj.items():
                result[key] = self._convert_secrets_to_dict(value)
            return result
            
        # Para listas e tuplas, converte cada elemento
        elif isinstance(secrets_obj, (list, tuple)):
            return [self._convert_secrets_to_dict(item) for item in secrets_obj]
            
        # Para tipos primitivos, retorna como está
        elif isinstance(secrets_obj, (str, int, float, bool)):
            return secrets_obj
            
        # Para outros tipos, tenta fazer uma cópia
        else:
            try:
                # Tenta converter para dict se possível
                if hasattr(secrets_obj, '__dict__'):
                    return copy.deepcopy(secrets_obj.__dict__)
                # Tenta conversão direta
                return copy.deepcopy(secrets_obj)
            except Exception:
                # Se tudo falhar, retorna o valor original
                return secrets_obj

    def _ensure_mutable_dict(self, data):
        """Garante que os dados sejam um dicionário Python mutável comum, não um objeto secrets"""
        import json
        import copy
        
        # Primeiro tenta a conversão recursiva
        try:
            converted = self._convert_secrets_to_dict(data)
            # Verifica se o resultado é um dicionário válido
            if isinstance(converted, dict) and len(converted) > 0:
                return converted
        except Exception as e:
            pass
        
        # Se a conversão recursiva falhar ou retornar algo inválido, tenta JSON
        try:
            # Apenas usa JSON se o objeto for serializável
            if hasattr(data, '__dict__') or isinstance(data, (dict, list, tuple, str, int, float, bool, type(None))):
                json_str = json.dumps(data, default=str)
                result = json.loads(json_str)
                # Verifica se o resultado é válido
                if isinstance(result, dict) and len(result) > 0:
                    return result
        except Exception as e:
            pass
        
        # Como último recurso, faz uma cópia profunda simples
        try:
            return copy.deepcopy(dict(data))
        except Exception:
            # Se tudo falhar, retorna os dados originais
            return data

    def get_user_credentials(self):
        """Obtém credenciais de usuário dos secrets do Streamlit ou arquivo local"""
        try:
            # Tenta primeiro os secrets do Streamlit (produção)
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'user_credentials'):
                # Converte o objeto secrets imutável em dict comum para permitir modificações
                secrets_data = st.secrets['user_credentials']
                # Usa conversão direta e robusta
                converted_data = self._convert_secrets_to_dict(secrets_data)
                return converted_data

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
                # Converte para dict se for um objeto secrets e cria uma cópia profunda
                secrets_data = st.secrets['google_sheets_credentials']
                # Usa conversão direta e robusta
                converted_data = self._convert_secrets_to_dict(secrets_data)
                return converted_data

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
