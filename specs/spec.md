# Spec — Encurtador de URLs (v1)

Este documento descreve **o que** o sistema faz e **por quê**. As decisões de
tecnologia estão em [plan.md](plan.md). Os princípios gerais estão em
[constitution.md](constitution.md).

## Intenção

Um encurtador de URLs que roda localmente. A pessoa informa uma URL longa e
recebe um link curto. Quem acessa o link curto é levado à URL original, e o
sistema conta quantas vezes isso aconteceu.

O sistema pode ser usado de duas formas: por uma **página web** (navegador) e
por uma **API** (JSON). As duas seguem exatamente as mesmas regras.

## Objetivos

- Encurtar uma URL, com código gerado automaticamente ou escolhido pela pessoa.
- Redirecionar o link curto para a URL original.
- Contar e exibir os cliques de cada link.
- Oferecer as mesmas funções pela página web e pela API.

## Não-objetivos (v1)

- Login e contas de usuário (planejado para uma versão futura).
- Expiração de links.
- Listar todos os links criados.
- Editar ou apagar links.
- Estatísticas além do total de cliques (datas, origem, navegador).

## Anti-objetivos

Coisas que tornariam o projeto um fracasso, mesmo funcionando:

- Regras diferentes entre a página e a API (ex.: a API aceita um código que a página recusa).
- Funcionalidades sem teste automatizado.
- Código tão "esperto" ou cheio de camadas que deixa de servir para aprender.

---

## Requisitos funcionais

### R1. Encurtar uma URL

A pessoa informa:
- **URL** (obrigatória)
- **Código personalizado** (opcional)

**Regras da URL**
- R1.1 Deve começar com `http://` ou `https://` e ter um domínio (ex.: `https://exemplo.com`).
- R1.2 Tamanho máximo de 2048 caracteres.
- R1.3 URL vazia ou inválida é recusada com uma mensagem clara, e nada é salvo.

**Regras do código personalizado**
- R1.4 Aceita **apenas letras e números** (`A–Z`, `a–z`, `0–9`). Nenhum caractere especial, espaço ou acento.
- R1.5 Tamanho entre **5 e 30** caracteres.
- R1.6 Maiúsculas e minúsculas são diferentes: `MeuLink` e `meulink` são códigos distintos.
- R1.7 Se o código já estiver em uso, a criação é recusada com a mensagem "esse código já está em uso". O link existente **nunca** é sobrescrito.
- R1.8 Alguns códigos são **reservados** e não podem ser escolhidos, porque colidem com páginas do sistema (atuais ou futuras). Lista inicial: `static`, `login`, `logout`, `admin`. A comparação ignora maiúsculas e minúsculas (`Login` também é recusado). A recusa usa a mesma mensagem de "já está em uso". O formato (R1.4, R1.5) é verificado **antes** da lista de reservados.
- R1.8a Código personalizado vazio ou só com espaços é tratado como "não informado", e o sistema gera um automaticamente.

**Código gerado automaticamente**
- R1.9 Sem código personalizado, o sistema gera um código aleatório de **6 caracteres** (letras e números).
- R1.10 O código gerado nunca repete um código existente nem um código reservado.

**Outros**
- R1.11 Encurtar a mesma URL duas vezes gera **dois links diferentes**, cada um com seu contador.
- R1.12 Todo link novo começa com **0 cliques**.

### R2. Redirecionar

- R2.1 Acessar `/<codigo>` leva a pessoa para a URL original.
- R2.2 Cada acesso soma **1 clique** ao link.
- R2.3 O redirecionamento deve acontecer a cada acesso, sem ser memorizado pelo navegador, para que todos os cliques sejam contados.
- R2.4 Um código inexistente mostra uma página "link não encontrado" com status 404, e nenhum clique é contado.

### R3. Ver informações de um link

- R3.1 É possível ver a URL original, o link curto e o total de cliques de um código.
- R3.2 Ver as informações **não** conta como clique.
- R3.3 Um código inexistente responde "link não encontrado" (404).

---

## Página web

### P1. Página inicial (`/`)
Formulário com dois campos: URL e código personalizado (opcional), mais o botão "Encurtar".

```
┌─────────────────────────────────────────┐
│  Encurtador de URLs                     │
│                                         │
│  URL:     [ https://...               ] │
│  Código:  [ (opcional)                ] │
│           [ Encurtar ]                  │
└─────────────────────────────────────────┘
```

### P2. Resultado
- Em caso de sucesso, mostra o link curto completo (ex.: `http://localhost:5000/aB3x9k`) e um link para a página de informações.
- Em caso de erro, mostra o formulário de novo com a mensagem de erro e **mantém o que a pessoa digitou**.

### P3. Página de informações (`/info/<codigo>`)
Mostra a URL original, o link curto e o total de cliques.

---

## API (JSON)

Todas as respostas são JSON. Os erros seguem o formato `{"erro": "mensagem"}`.

### A1. Criar link — `POST /api/links`

Corpo:
```json
{ "url": "https://exemplo.com/pagina", "codigo": "opcional" }
```

| Situação | Status | Resposta |
|---|---|---|
| Criado | 201 | `{"codigo": "aB3x9k", "url": "https://...", "curto": "http://localhost:5000/aB3x9k", "cliques": 0}` |
| URL ou código inválido | 400 | `{"erro": "..."}` |
| Corpo ausente, não é JSON, ou `url`/`codigo` não são texto | 400 | `{"erro": "..."}` |
| Código já em uso ou reservado | 409 | `{"erro": "esse código já está em uso"}` |

### A2. Consultar link — `GET /api/links/<codigo>`

| Situação | Status | Resposta |
|---|---|---|
| Encontrado | 200 | `{"codigo": "...", "url": "...", "curto": "...", "cliques": 12}` |
| Não existe | 404 | `{"erro": "link não encontrado"}` |

---

## Critérios de aceite

- [ ] Encurtar pela página e pela API produz links que funcionam no navegador.
- [ ] Um código personalizado válido é usado exatamente como informado.
- [ ] Códigos com caracteres especiais, com menos de 5 ou mais de 30 caracteres, são recusados pela página **e** pela API.
- [ ] Um código repetido ou reservado é recusado, e o link original continua intacto.
- [ ] Cada acesso ao link curto soma exatamente 1 clique. Ver as informações não soma.
- [ ] Código inexistente → 404 no redirecionamento, na página de info e na API.
- [ ] Todos os requisitos acima têm teste automatizado passando.

## Versões futuras

- Login de usuários, com links associados a quem os criou.
- Listagem, edição e exclusão de links.
- Expiração de links.
