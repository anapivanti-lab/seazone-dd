"""Estruturas de dados centrais do sistema."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class TipoPessoa(str, Enum):
    PJ = "PJ"  # franquia (CNPJ)
    PF = "PF"  # operador / representante legal (CPF)


class Status(str, Enum):
    SUCESSO = "sucesso"            # certidão emitida e salva
    PENDENTE = "pendente_captcha"  # aguardando você resolver o captcha / calibrar
    INDISPONIVEL = "indisponivel"  # não dá para emitir (pago / presencial / sem versão eletrônica)
    ERRO = "erro"                  # falha técnica


def so_digitos(valor: str) -> str:
    """Remove tudo que não for número (pontos, traços, barras de CNPJ/CPF)."""
    return re.sub(r"\D", "", valor or "")


@dataclass
class Contexto:
    """Dados de entrada de uma due diligence."""

    tipo: TipoPessoa
    documento: str               # CNPJ ou CPF (apenas dígitos)
    nome: str = ""               # razão social / nome completo
    uf: str = ""                 # ex.: "SC"
    municipio: str = ""          # ex.: "Florianópolis"
    rg: str = ""                 # RG (certidões judiciais de pessoa física)
    nome_mae: str = ""           # nome da mãe (idem)
    endereco: str = ""           # endereço (idem)
    data_nascimento: str = ""    # data de nascimento (idem)
    pasta_saida: Optional[Path] = None

    def __post_init__(self):
        self.documento = so_digitos(self.documento)
        self.uf = (self.uf or "").strip().upper()


@dataclass
class Resultado:
    """O que cada provedor devolve depois de tentar emitir uma certidão."""

    provedor: str                # nome legível da certidão
    status: Status
    arquivo: Optional[Path] = None
    mensagem: str = ""           # motivo quando indisponível/erro/pendente
