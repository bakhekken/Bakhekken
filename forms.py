from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from flask_wtf.file import FileField, FileAllowed

class LoginForm(FlaskForm):
    username = StringField("Brukarnamn", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Passord", validators=[DataRequired()])
    submit = SubmitField("Logg inn")

class PageEditForm(FlaskForm):
    title = StringField("Tittel", validators=[DataRequired(), Length(max=120)])
    slug = StringField("Adresse namn slug", validators=[DataRequired(), Length(max=80)])
    is_hidden = BooleanField("Skjul sida frå meny og framside")

    card_enabled = BooleanField("Vis kort på framsida")
    card_title = StringField("Korttittel", validators=[Optional(), Length(max=120)])
    card_image = FileField("Bilete til kort", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Berre bilete")])

    content_html = TextAreaField("Innhald", validators=[Optional()])
    submit = SubmitField("Lagre")

class SettingsForm(FlaskForm):
    site_title = StringField("Tittel på nettsida", validators=[DataRequired(), Length(max=120)])
    primary_color = StringField("Hovudfarge hex", validators=[DataRequired(), Length(max=20)])
    font_family = StringField("Skrift font family", validators=[DataRequired(), Length(max=160)])
    submit = SubmitField("Lagre")

class UploadForm(FlaskForm):
    file = FileField("Last opp bilete", validators=[DataRequired(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Berre bilete")])
    submit = SubmitField("Last opp")
