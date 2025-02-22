function resetRevision() {
    // Find the revision textarea and update its value
    window.prodigy.update({ question: window.prodigy.content.question_orig });
    window.prodigy.update({ choice_A: window.prodigy.content.choice_A_orig });
    window.prodigy.update({ choice_B: window.prodigy.content.choice_B_orig });
    window.prodigy.update({ choice_C: window.prodigy.content.choice_C_orig });
    window.prodigy.update({ choice_D: window.prodigy.content.choice_D_orig });
}