class Puppet::Provider::Mongodb < Puppet::Provider

  # Without initvars commands won't work.
  initvars
  commands :mongo => 'mongo'

  # Optional defaults file
  def self.mongorc_file
    if File.file?("#{Facter.value(:root_home)}/.mongorc.js")
      "load('#{Facter.value(:root_home)}/.mongorc.js'); "
    else
      nil
    end
  end

  def mongorc_file
    self.class.mongorc_file
  end

  # Mongo Command Wrapper
  def self.mongo_eval(cmd, db = 'admin')
    if mongorc_file
        cmd = mongorc_file + cmd
    end

    out = mongo([db, '--quiet', '--eval', cmd])

    out.gsub!(/ObjectId\(([^)]*)\)/, '\1')
    out
  end

  def mongo_eval(cmd, db = 'admin')
    self.class.mongo_eval(cmd, db)
  end

  # Mongo Version checker
  def self.mongo_version
    @@mongo_version ||= self.mongo_eval('db.version()')
  end

  def mongo_version
    self.class.mongo_version
  end

  def self.mongo_24?
    v = self.mongo_version
    ! v[/^2\.4\./].nil?
  end

  def mongo_24?
    self.class.mongo_24?
  end

end
