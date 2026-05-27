# Supported informe sources — IRPF 2026

Institutions detected in the reference declaration (synthetic fixture).
These are the sources whose informes would be worth building parsers for.
No concrete parser ships yet — each needs a real sample informe.

| Instituição | CNPJ | Aparece em |
|---|---|---|
| — | 10264663000177 | REG_BEM |
| — | 30680829000143 | REG_BEM |
| 60.780.726 JOAO DA SILVA SANTOS DE TEST | — | REG_RENDIMENTO_ISENTO_TIPO_INFORMACAO_3 |
| BANCOSEGURO S.A. | — | REG_RENDIMENTO_EXCLUSIVO_TIPO_INFORMACAO_2 |
| CLINICA MEDICA ALTIKES | — | REG_PAGAMENTO |
| NU FINANCEIRA S.A. - SOCIEDADE DE CREDITO, FINANCIAMENTO E I | — | REG_RENDIMENTO_EXCLUSIVO_TIPO_INFORMACAO_2 |
| NU INVESTIMENTOS S.A. | — | REG_RENDIMENTO_EXCLUSIVO_TIPO_INFORMACAO_2 |
| TKS SISTEMA HOSPITALARES E CONSULTORIOS MEDICOS SA | — | REG_PAGAMENTO |
| UNIMED LESTE PAULISTA COOPERATIVA DE TRABALHO MEDICO | — | REG_PAGAMENTO |

## Adding a parser

See `packages/irpf_core/src/irpf_core/informes/__init__.py` for the
`InformeParser` protocol and `register()`. Provide a real (redacted)
sample of the informe so the parser can be built and tested.
