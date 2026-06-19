#ifndef TRAININGWIDGET_H
#define TRAININGWIDGET_H

#include <QWidget>
#include <QProcess>
#include <QPlainTextEdit>
#include <QLineEdit>
#include <QPushButton>
#include <QStackedWidget>

class CarSearchWidget;
class CarEvaluationWidget;

class TrainingWidget : public QWidget
{
    Q_OBJECT

public:
    explicit TrainingWidget(QWidget *parent = nullptr);
    ~TrainingWidget();

signals:
    void backToMainMenuRequested();

private slots:
    void onRunTrainingClicked();
    void onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void readProcessOutput();
    void readProcessError();
    void sendUserInput();
    void showTrainingMenu();

private:
    void setupUi();
    void appendOutput(const QString &text);
    void appendError(const QString &text);

    QProcess *trainingProcess;

    QStackedWidget *stackedWidget;
    QWidget *menuContainerWidget;
    CarSearchWidget *searchWidget;
    CarEvaluationWidget *evaluationWidget;

    QPlainTextEdit *outputTextEdit;
    QLineEdit *inputLineEdit;
    QPushButton *runButton;
    QPushButton *backButton;
    QPushButton *sendButton;

    bool waitingForInput;
};

#endif // TRAININGWIDGET_H