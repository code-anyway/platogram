import platogram
import pytest
from platogram.ops import chunk_text, get_paragraphs, parse


def test_get_paragraphs() -> None:
    llm = platogram.llm.get_model("anthropic/claude-3-5-sonnet")
    text = "In this video, we're going to talk about the basics of machine learning.【0】Machine learning is a field of artificial intelligence that focuses on building algorithms that can learn from data and make predictions or decisions without being explicitly programmed.【1】There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning.【2】Supervised learning involves training a model on labeled data, where the correct output is known for each input.【3】The goal is for the model to learn a mapping from inputs to outputs that can be applied to new, unseen data.【4】Unsupervised learning, on the other hand, involves finding patterns or structure in unlabeled data.【5】The model is not given any explicit guidance on what the correct output should be.【6】Reinforcement learning is a type of machine learning where an agent learns to make decisions by interacting with an environment and receiving rewards or punishments based on its actions.【7】The goal is for the agent to learn a policy that maximizes its cumulative reward over time.【8】Machine learning has many practical applications, such as image recognition, natural language processing, and recommendation systems.【9】It's an exciting and rapidly evolving field with the potential to transform many industries and solve complex problems.【10】"
    paragraphs = get_paragraphs(
        text, llm, max_tokens=2048, temperature=0.5, chunk_size=1024
    )
    assert len(paragraphs) > 2
    
    
def test_get_paragraphs_es() -> None:
    llm = platogram.llm.get_model("anthropic/claude-3-5-sonnet")
    text = "En este video, vamos a hablar sobre los fundamentos del aprendizaje automático.【0】El aprendizaje automático es un campo de la inteligencia artificial que se centra en la construcción de algoritmos que pueden aprender de los datos y hacer predicciones o tomar decisiones sin ser programados explícitamente.【1】Existen tres tipos principales de aprendizaje automático: aprendizaje supervisado, aprendizaje no supervisado y aprendizaje por refuerzo.【2】El aprendizaje supervisado implica entrenar un modelo con datos etiquetados, donde se conoce la salida correcta para cada entrada.【3】El objetivo es que el modelo aprenda un mapeo de entradas a salidas que pueda aplicarse a datos nuevos y no vistos.【4】El aprendizaje no supervisado, por otro lado, implica encontrar patrones o estructuras en datos no etiquetados.【5】Al modelo no se le da ninguna guía explícita sobre cuál debería ser la salida correcta.【6】El aprendizaje por refuerzo es un tipo de aprendizaje automático donde un agente aprende a tomar decisiones interactuando con un entorno y recibiendo recompensas o castigos basados en sus acciones.【7】El objetivo es que el agente aprenda una política que maximice su recompensa acumulada a lo largo del tiempo.【8】El aprendizaje automático tiene muchas aplicaciones prácticas, como el reconocimiento de imágenes, el procesamiento del lenguaje natural y los sistemas de recomendación.【9】Es un campo emocionante y en rápida evolución con el potencial de transformar muchas industrias y resolver problemas complejos.【10】"
    paragraphs = get_paragraphs(
        text, llm, max_tokens=2048, temperature=0.5, chunk_size=1024, lang="es"
    )
    assert len(paragraphs) > 2


def test_chunk_empty_input_string():
    with pytest.raises(ValueError, match="Input string cannot be empty."):
        chunk_text("", chunk_size=10, token_count_fn=len)


def test_chunk_size_smaller_than_smallest_segment():
    text_with_markers = "Hello【1】world【2】!【3】"
    chunk_size = 2
    token_count_fn = len
    expected_chunks = ["Hello【1】", "world【2】", "!【3】"]
    assert chunk_text(text_with_markers, chunk_size, token_count_fn) == expected_chunks


def test_chunk_size_equal_to_total_tokens():
    text_with_markers = "Hello【1】world【2】!【3】"
    chunk_size = len(text_with_markers)
    token_count_fn = len
    expected_chunks = ["Hello【1】world【2】!【3】"]
    assert chunk_text(text_with_markers, chunk_size, token_count_fn) == expected_chunks


def test_chunk_size_larger_than_total_tokens():
    text_with_markers = "Hello【1】world【2】! 【3】"
    chunk_size = len(text_with_markers) + 1
    token_count_fn = len
    expected_chunks = ["Hello【1】world【2】! 【3】"]
    assert chunk_text(text_with_markers, chunk_size, token_count_fn) == expected_chunks


def test_empty_segments():
    text_with_markers = "【1】Hello【2】【3】world【4】!【5】"
    chunk_size = 14
    token_count_fn = len
    expected_chunks = ["【1】Hello【2】", "【3】world【4】", "!【5】"]
    assert chunk_text(text_with_markers, chunk_size, token_count_fn) == expected_chunks


def test_consecutive_markers():
    text_with_markers = "Hello【1】【2】world【3】!【4】"
    chunk_size = 15
    token_count_fn = len
    expected_chunks = ["Hello【1】【2】", "world【3】!【4】"]
    assert chunk_text(text_with_markers, chunk_size, token_count_fn) == expected_chunks


def test_parse_basic():
    text = "hello【1】world!【2】"
    expected = {1: "hello", 2: "world!"}
    assert parse(text) == expected


def test_parse_empty_string():
    text = ""
    with pytest.raises(ValueError, match="Input string cannot be empty."):
        parse(text)


def test_parse_trailing_text():
    text = "hello【1】world!【2】trailing text"
    with pytest.raises(ValueError, match="Input string must end with a valid marker."):
        parse(text)


def test_parse_duplicate_markers():
    text = "hello【1】world【2】!【1】"
    expected = {1: "hello!", 2: "world"}
    assert parse(text) == expected


def test_parse_non_numeric_markers():
    text = "hello【a】world【b】"
    with pytest.raises(
        ValueError, match="Input string does not contain any valid markers."
    ):
        parse(text)


def test_parse_leading_trailing_whitespace():
    text = "  hello 【1】 world! 【2】"
    expected = {1: "  hello ", 2: " world! "}
    assert parse(text) == expected


def test_parse_multiple_segments():
    text = "segment1【1】segment2【2】segment3【3】"
    expected = {1: "segment1", 2: "segment2", 3: "segment3"}
    assert parse(text) == expected
