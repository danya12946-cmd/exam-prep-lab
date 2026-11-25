from django.db import migrations

FORWARD_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS exams_one_correct_option_per_question
    ON exams_answeroption (question_id) WHERE is_correct;

CREATE OR REPLACE FUNCTION exams_check_question_options(p_question_id integer)
RETURNS void AS $$
DECLARE
    v_options integer;
    v_correct integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM exams_question WHERE id = p_question_id) THEN
        RETURN;
    END IF;

    SELECT COUNT(*), COUNT(*) FILTER (WHERE is_correct)
      INTO v_options, v_correct
      FROM exams_answeroption
     WHERE question_id = p_question_id;

    IF v_options < 2 OR v_options > 6 THEN
        RAISE EXCEPTION 'Вопрос должен иметь от 2 до 6 вариантов ответа'
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_correct <> 1 THEN
        RAISE EXCEPTION 'Вопрос должен иметь ровно один правильный вариант'
            USING ERRCODE = 'check_violation';
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION exams_answer_options_integrity() RETURNS trigger AS $$
BEGIN
    IF TG_OP <> 'INSERT' THEN
        PERFORM exams_check_question_options(OLD.question_id);
    END IF;
    IF TG_OP <> 'DELETE' THEN
        PERFORM exams_check_question_options(NEW.question_id);
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS exams_answer_options_integrity ON exams_answeroption;

CREATE CONSTRAINT TRIGGER exams_answer_options_integrity
    AFTER INSERT OR UPDATE OR DELETE ON exams_answeroption
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION exams_answer_options_integrity();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS exams_answer_options_integrity ON exams_answeroption;
DROP FUNCTION IF EXISTS exams_answer_options_integrity();
DROP FUNCTION IF EXISTS exams_check_question_options(integer);
DROP INDEX IF EXISTS exams_one_correct_option_per_question;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("exams", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
