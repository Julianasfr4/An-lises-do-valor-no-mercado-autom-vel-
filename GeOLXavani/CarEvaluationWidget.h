#ifndef CAREVALUATIONWIDGET_H
#define CAREVALUATIONWIDGET_H

#include <QWidget>
#include <QProcess>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QComboBox>
#include <QSpinBox>
#include <QPlainTextEdit>

class CarEvaluationWidget : public QWidget
{
    Q_OBJECT

public:
    explicit CarEvaluationWidget(QWidget *parent = nullptr);
    ~CarEvaluationWidget();

signals:
    void backToTrainingRequested();

private slots:
    void onEvaluateClicked();
    void onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void readProcessOutput();

private:
    void setupUi();

    QProcess *evaluationProcess;

    QLineEdit *brandInput;
    QLineEdit *modelInput;
    QSpinBox *yearSpinBox;
    QSpinBox *priceSpinBox;
    QSpinBox *kmSpinBox;
    QComboBox *fuelTypeCombo;
    QComboBox *transmissionCombo;

    QPushButton *evaluateButton;
    QPushButton *backButton;
    QLabel *resultLabel;
    QPlainTextEdit *detailsTextEdit;
};

#endif // CAREVALUATIONWIDGET_H