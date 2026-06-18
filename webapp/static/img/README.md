# Imagens do esquema da UHR

Esta pasta contém os recursos estáticos usados pelo modal de visualização
gráfica da usina (em `templates/result.html`).

## Arquivos necessários

| Arquivo           | Descrição                                                                 |
|-------------------|---------------------------------------------------------------------------|
| `fundo_uhr.png`   | Imagem de fundo do esquema (corte lateral com Reservatório Superior e Inferior). |
| `casa_forca.png`  | Imagem da casa de força (fundo transparente) sobreposta na posição da usina.     |

Coloque os dois arquivos diretamente nesta pasta (`webapp/static/img/`).
Eles são servidos pelo Flask via `url_for('static', filename='img/<arquivo>')`.

> Caso algum arquivo esteja ausente, o modal ainda abre e desenha os tubos,
> apenas sem a imagem correspondente ao fundo.
