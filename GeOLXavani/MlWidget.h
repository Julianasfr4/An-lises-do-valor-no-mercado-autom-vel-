#ifndef MLWIDGET_H
#define MLWIDGET_H

#include <QWidget>
#include <QPushButton>
#include <QLabel>
#include <QPlainTextEdit>
#include <QLineEdit>
#include <QProcess>

class MlWidget : public QWidget
{
    Q_OBJECT

public:
    explicit MlWidget(QWidget *parent = nullptr);
    ~MlWidget();

signals:
    void backToMainMenuRequested(); // Comunica com o QStackedWidget da MainWindow

private slots:
    void onRunTrainingClicked();
    void onShowGraphsClicked(); // Reativado para abrir a janela com o gráfico real
    void onTrainingFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void readTrainingOutput();
    void sendUserInput();

private:
    void setupUi();

    QPushButton *backButton;
    QPushButton *runTrainingButton;
    QPushButton *showGraphsButton; // Reativado
    QLabel *statusLabel;
    QPlainTextEdit *consoleLog;

    QLineEdit *inputLineEdit;
    QPushButton *sendButton;

    QProcess *mlProcess;
};

#endif // MLWIDGET_H