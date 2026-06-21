from app.ui.flashcards_sections import (
    FC_MAIN_SECTION_CREATE,
    FC_MAIN_SECTION_DECKS,
    FC_MAIN_SECTION_REVIEW,
    e2e_source_labels,
    section_order_and_labels,
)


def test_flashcards_section_order_and_labels_contract():
    order, labels = section_order_and_labels()
    assert order == [FC_MAIN_SECTION_DECKS, FC_MAIN_SECTION_CREATE, FC_MAIN_SECTION_REVIEW]
    assert labels[FC_MAIN_SECTION_DECKS]
    assert labels[FC_MAIN_SECTION_CREATE]
    assert labels[FC_MAIN_SECTION_REVIEW]


def test_flashcards_source_labels_contract():
    doc_label, upload_label = e2e_source_labels()
    assert "Документ" in doc_label
    assert "Загрузить" in upload_label
